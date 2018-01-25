import datetime
import time

import dataset
import fakeredis
import tabulate
import termcolor
from flask import request, Flask, jsonify

app = Flask(__name__)
redis = fakeredis.FakeStrictRedis()
db = dataset.connect('sqlite:///')

# redis key: 保存全局期数
GLOBAL_PERIOD_NUMBER = 'global_period_number'
# redis key: 期数预分配号码队列
PREALLOCATE_QUEUE = 'free_meals_preallocated_queue'

# 霸王餐号码分配数
ALLOCATED_NUMBER = 3
# 霸王餐号码起始
CODE_START = 10001


@app.route('/preallocate_codes', methods=['POST'])
def preallocate_codes():
    """预分配参与号码服务,生成下一个期数的中奖号码放入预分配队列中"""
    # 获取下一期期数
    period_number = redis.incr(GLOBAL_PERIOD_NUMBER)

    # 预生成对应号码放入队列中, 格式为 '{期数}_{参与号码}'
    period_codes = []
    for code in range(CODE_START, CODE_START + ALLOCATED_NUMBER):
        key = '{period_number}_{code}'.format(period_number=period_number, code=code)
        period_codes.append(key)
    redis.lpush(PREALLOCATE_QUEUE, *period_codes)

    termcolor.cprint('# 预分配期数 {} 号码池到队列成功'.format(period_number), 'red')
    print_redis_value()
    return jsonify({'message': 'ok', 'generate_period': period_number}), 201


#### 分发号码模块

# redis key: 用于累加每一期用户参与的时间戳, 用于后期开奖的计算，避免从数据库读取
PERIOD_CUMULATIVE_TIME = '{}_CUMULATIVE_TIME'

# redis 列表 key: 用于保存每一期参与用户的 uid，用于直接获取中奖用户，避免从数据库读取
# 存储形式形如 [uid0, uid1, ..., uid29], 这样 uid0 就是对应余数为 0，中奖号码为 10001 的情况
PERIOD_INVOLVED_USERS = '{}_involved_users'


class FREE_MEALS_STATUS:
    START = 0
    FINISH = 1


@app.route('/pay_success_callback', methods=['GET'])
def get_pay_success_callback():
    """处理用户支付成功后获取参与号码的逻辑"""

    uid = int(request.args['uid'])
    # 从队列中获取一个预分配字段，然后 parse 出对应的期数和参与号码
    _, period_code = redis.brpop(PREALLOCATE_QUEUE)  # 此时 period_code 类似 b'{期数}_{参与号码}', 比如 b'00001_10001'
    period_str, code_str = period_code.decode().split('_')  # 假设 period 为 '00001', 参与号码为 '10001'
    code = int(code_str)
    period = int(period_str)

    # debug: 打印取出一个号码后的队列情况
    termcolor.cprint('\n# 用户 {} 取出 号码 {} 后的队列情况'.format(uid, period_code), 'red')
    print_redis_value()

    # 如果是第一次获取对应期数的参与号码，则在数据表 free_meals 中插入当期情况。
    # 也可以选择把这个过程放到预分配函数中做, 但是这样的话 created_at 记录的就不是期数真正开始的时间，只是预分配的时间
    if code == CODE_START:  # 如果 paser 出来的号码为当期第一个获取的开奖号码，则插入当期信息到表 free_meals
        insert_new_period_to_db(id=period, status=FREE_MEALS_STATUS.START)

        # 因为号码为初始化号码，所以插入当期信息到表 free_meals
        termcolor.cprint('\n# 因为号码 {} 为初始化号码，所以插入当期信息到表 free_meals'.format(code), 'red')
        print_db_free_meal_table()

    # 生成用户获得参与号码的时间戳
    allocated_time = created_current_ms_time()  # 算法为 int(time.time() * 1000)

    # 插入相关信息到数据库
    insert_new_detail_to_db(period=period, uid=uid, code=code, allocated_time=allocated_time)

    # debug: 打印插入 detail 的数据库情况
    termcolor.cprint('\n# 插入用户号码分配情况到数据库', 'red')
    print_db_table('free_meal_details')

    # 累加时间戳的结果到 redis 的中, 这样开奖时就不需要再从数据库获取了
    period_cumulative_time_key = PERIOD_CUMULATIVE_TIME.format(period)  # 初始化对应期数累加时间的 key
    redis.incrby(period_cumulative_time_key, allocated_time)

    # 添加 uid 到对应期数的参与用户队列中, 这样开奖时计算出余数后可以直接用 redis.lindex 方法获取对应余数的中奖用户
    period_involved_users_key = PERIOD_INVOLVED_USERS.format(period)  # 初始化对应期数保存获奖用户的 key
    redis.rpush(period_involved_users_key, uid)  # 从右侧 push uid 到队列中, 这样lindex(n) 就对应余数为 n 时的中奖用户,中奖号码为 CODE_START + n

    # debug: 打印缓存的时间累加值以及分配号码的用户列表
    termcolor.cprint('\n# 打印缓存的时间累加值以及分配号码的用户列表', 'red')
    print_redis_value()

    code_end = CODE_START + ALLOCATED_NUMBER - 1  # 此时为 10030
    # 如果是当期最后一个号码，则进入开奖逻辑
    if code == code_end:
        # debug
        termcolor.cprint('\n# 期数 {} 最后一个号码 {} 被取完，触发预分配，并进入开奖过程'.format(period, code), 'red')
        # 预生成下一期的参与号码以保持平衡
        preallocate_codes()
        # 进入开奖过程
        open_lottery(period)
    return jsonify({'message': 'ok'}), 200


# 开奖服务
def open_lottery(period):
    """计算对应期数开奖结果并写入数据库
    :param period: 开奖期数"""
    # 获取对应期数所有用户的时间累加值
    # debug
    termcolor.cprint('\n# 对 {} 期进行开奖'.format(period), 'red')
    print_redis_value()

    period_cumulative_time_key = PERIOD_CUMULATIVE_TIME.format(period)  # 初始化对应期数累加时间的 key
    cumulative_time = int(redis.get(period_cumulative_time_key))

    # 根据时间累加值求余数, 用于计算中奖号码和获取中奖用户
    winner_mod = cumulative_time % ALLOCATED_NUMBER

    # 根据余数计算中奖号码
    winner_code = CODE_START + winner_mod

    # 从缓存的参与用户列表中获取中奖用户
    period_involved_users_key = PERIOD_INVOLVED_USERS.format(period)  # 初始化对应期数保存参与用户的 key
    winner_uid = redis.lindex(period_involved_users_key, winner_mod).decode()

    # 删除 redis 缓存的当期时间累加值和参与用户列表
    redis.delete(period_cumulative_time_key, period_involved_users_key)
    # 更新开奖结果到表 free_meals, 并设置对应期数状态为 1 以及对应的结束时间
    update_free_meals_period_set_winner(period, winner_uid, winner_code)

    # debug
    termcolor.cprint('\n# 余数计算结果: {} 获奖号码: {} 获奖用户: {}'.format(winner_mod, winner_code, winner_uid), 'red')
    print_db_table('free_meal_winners')
    termcolor.cprint('# 更新 free_meals 表设置对应期数状态为 finish, 并设置中奖用户，中奖号码和结束时间,以及删除不用的 redis 缓存', 'red')
    print_db_free_meal_table()


# model
def insert_new_period_to_db(id, status):
    table_name = 'free_meals'
    table = db[table_name]
    table.insert({'period': id,
                  'status': int(status),
                  'created_at': datetime.datetime.now(),
                  'winner_uid': 0,
                  'winner_code': 0,
                  'finished_at': datetime.datetime.now()})


def insert_new_detail_to_db(period, uid, code, allocated_time):
    table_name = 'free_meal_details'
    db[table_name].insert({'period': period,
                           'uid': uid,
                           'code': code,
                           'allocated_time': allocated_time,
                           'created_at': datetime.datetime.now()})


def update_free_meals_period_set_winner(period, winner_uid, winner_code):
    table_name = 'free_meals'
    db[table_name].update({'period': period,
                           'status': FREE_MEALS_STATUS.FINISH,
                           'winner_uid': winner_uid,
                           'winner_code': winner_code,
                           'finished_at': datetime.datetime.now()}, ['period'])


# utils
def created_current_ms_time():
    return int(time.time() * 1000)


def print_db_table(name):
    try:
        rows = list(db[name])
    except TypeError:
        return
    termcolor.cprint('{} 表:'.format(name), 'green')
    print(tabulate.tabulate(rows, headers='keys'))


def print_db_free_meal_table():
    name = 'free_meals'
    termcolor.cprint('{} 表:'.format(name), 'green')
    rows = list(db[name])
    for row in rows:
        row['id'] = row['period']
        del row['period']
    print(tabulate.tabulate(rows, headers='keys'))


def print_db():
    termcolor.cprint('数据库情况: ', 'red')
    print_db_free_meal_table()
    for name in {'free_meal_details', 'free_meal_winners'}:
        print_db_table(name)


def print_redis_value():
    termcolor.cprint('redis 数据存储情况:', 'green')
    print('全局期数id {} 为: '.format(GLOBAL_PERIOD_NUMBER), end='')

    current_period = int(redis.get(GLOBAL_PERIOD_NUMBER))
    termcolor.cprint('{}'.format(current_period))

    print('缓存的中奖号码队列:', end='')
    li = redis.lrange(PREALLOCATE_QUEUE, 0, -1)
    termcolor.cprint('{}'.format(li))

    for period in range(0, current_period + 1):
        period_involved_users_key = PERIOD_INVOLVED_USERS.format(period)  # 初始化对应期数保存获奖用户的 key
        if not redis.exists(period_involved_users_key):
            continue

        termcolor.cprint('期数 {} 对应的用户存储情况: '.format(period), end='')
        li = redis.lrange(period_involved_users_key, 0, -1)
        termcolor.cprint('{}'.format(li))

        termcolor.cprint('期数 {} 对应的时间戳累加情况: '.format(period), end='')
        period_cumulative_time_key = PERIOD_CUMULATIVE_TIME.format(period)  # 初始化对应期数累加时间的 key
        value = int(redis.get(period_cumulative_time_key))
        termcolor.cprint('{}'.format(value))


if __name__ == '__main__':
    app.run(debug=True)
