## 饿了么霸王餐基本实现思路

饿了么的霸王餐我很久就在 app 看到了，但是一直没用过。最近我试用了下，下面就来分析下如何实现类似饿了么霸王餐的功能

### 霸王餐流程分析

发现霸王餐有 30 元 和 plus 300 元 两种，但是流程类似，下面为了简化仅讨论 30 元 霸王餐的架构

1. 用户进入霸王餐页面，能看到以下数据:
    * 本期信息: 期数、总需人次、剩余人次
    * 本期参与人: 用户名、参与时间
    * 中奖直播: 用户名、时间
2. 选择立即参与后会跳转到中奖结果页面，因为饿了么用户数较多，所以没有看到等待开奖的过程
    * 中奖结果的计算为 将所有用户的参与时间变为毫秒整型后累加 对参与人数(这里是30) 求余数 + 10001 构成
3. 中奖界面数据可分为两类
    * 本期中奖结果: 期数、中奖号码、中奖用户、中奖用户参与时间
    * 本人投注结果: 参与次数、参与号码 (参与次数可由参与号码得出)
    * 本期参与人: 用户名、参与时间

以上需要注意的是：
* 用户在霸王餐看到的参与期数跟实际付款之后获得的期数不同，不要求一致性
* 用户参与时间单位到毫秒
* 号码从 10001 到 10030
* 用户每次只能支付 1 元获取一个号码，这样就避免了投注多时临界值的问题

### 表设计

通过上文就可以根据对应的数据建表了

#### free_meals 霸王餐期数表

主要用于保存霸王餐每期任务的情况

* `id` int: 霸王餐期数
* `created_at` datetime: 保存任务创建时间
* `finished_at` datetime: 开奖时间, 开奖时设置
* `winner_uid` int: 获奖用户 id, 开奖时设置
* `winner_code` int: 获奖号码, 开奖时设置
* `status` int: 霸王餐状态 0 为进行中，1 为开奖结束

#### free_meal_details 霸王餐用户号码详情表

* `id` int: 自增 id
* `period` int: 霸王餐期数
* `uid` int: 用户 id
* `code` int: 拿到的参与号码
* `allocate_time` int: 参与时间，为毫秒级别时间戳
* `created_at` datetime: 创建时间


### 设计思路

因为饿了么的霸王餐用户较多，引入 redis 作为缓存、队列、全局 id 生成器。

* 初期在 redis 队列中缓存一定期数的号码，缓存期数具体取决于实际情况

* 在分发号码时，当本期的号码取完时调用 `预分配期数模块` 生成下一期号码放入队列以保持队列平衡

* 缓存用户的时间戳累加值和分发号码的用户到 redis 中，避免最后开奖时需要从数据库读取


#### redis 的作用

* 用于生成全局递增的期数 id
* 预生成一定期数的号码放入 redis 的队列中，便于用户获取号码
   * 假设预分配 100 期，key 以 {期数}_{号码} 的形式放入队列中
   * 每当客户端获取完一期的所有号码时(可由分发的号码为 `10030` 判断)，此时异步调用 `预分配期数模块` 生成下一期的号码池加入队列
   * 预分配的数量由线上实际情况决定
* 用列表按顺序缓存分发号码的用户以及缓存每期用户的时间累加值, 这样求结果时就不需要在查询数据库了

### 服务划分

分为三个主模块

* 预分配期数模块: 预先分配下一期号码到缓存队列
* 分发号码模块：向用户分发指定号码，并执行相关的初始化／开奖逻辑
* 开奖模块: 执行对应期数的开奖逻辑并写入数据库

一个辅助模块

* 初始化模块: 调用预分配任务模块,可以在最开始指定先预分配多少期的中奖号码


### 实现伪代码

#### 预分配任务模块

生成下一个期数的中奖号码放入预分配队列中

```python
# redis key: 保存全局期数
GLOBAL_PERIOD_NUMBER = 'global_period_number'
# redis key: 期数预分配号码队列
PREALLOCATE_QUEUE = 'free_meals_preallocated_queue'

# 霸王餐号码分配数
ALLOCATED_NUMBER = 30
# 霸王餐号码起始
CODE_START = 10001


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
```


#### 分发号码模块
向用户分发指定号码，并执行相关的初始化／开奖逻辑

```python
# redis key: 用于累加每一期用户参与的时间戳, 用于后期开奖的计算，避免从数据库读取
PERIOD_CUMULATIVE_TIME = '{}_CUMULATIVE_TIME'

# redis 列表 key: 用于保存每一期参与用户的 uid，用于直接获取中奖用户，避免从数据库读取
# 存储形式形如 [uid0, uid1, ..., uid29], 这样 uid0 就是对应余数为 0，中奖号码为 10001 的情况
PERIOD_INVOLVED_USERS = '{}_involved_users'


class FREE_MEALS_STATUS:
    START = 0
    FINISH = 1


def get_pay_success_callback(uid):
    """处理用户支付成功后获取参与号码的逻辑"""
    # 从队列中获取一个预分配字段，然后 parse 出对应的期数和参与号码
    _, period_code = redis.brpop(PREALLOCATE_QUEUE)  # 此时 period_code 类似 b'{期数}_{参与号码}', 比如 b'00001_10001'
    period, code_str = period_code.decode().split('_')  # 假设 period 为 '00001', 参与号码为 '10001'
    code = int(code_str)

    # 如果是第一次获取对应期数的参与号码，则在数据表 free_meals 中插入当期情况。
    # 也可以选择把这个过程放到预分配函数中做, 但是这样的话 created_at 记录的就不是期数真正开始的时间，只是预分配的时间
    if code == CODE_START:  # 如果 paser 出来的号码为当期第一个获取的开奖号码，则插入当期信息到表 free_meals
        insert_new_period_to_db(id=period, status=FREE_MEALS_STATUS.START)

    # 生成用户获得参与号码的时间戳
    allocated_time = created_current_ms_time()  # 算法为 int(time.time() * 1000)

    # 插入相关信息到数据库
    insert_new_detail_to_db(period=period, uid=uid, code=code, allocated_time=allocated_time)

    # 累加时间戳的结果到 redis 的中, 这样开奖时就不需要再从数据库获取了
    period_cumulative_time_key = PERIOD_CUMULATIVE_TIME.format(period)  # 初始化对应期数累加时间的 key
    redis.incrby(period_cumulative_time_key, allocated_time)

    # 添加 uid 到对应期数的参与用户队列中, 这样开奖时计算出余数后可以直接用 redis.lindex 方法获取对应余数的中奖用户
    period_involved_users_key = PERIOD_INVOLVED_USERS.format(period)  # 初始化对应期数保存获奖用户的 key
    redis.rpush(period_involved_users_key, uid)  # 从右侧 push uid 到队列中, 这样lindex(n) 就对应余数为 n 时的中奖用户,中奖号码为 CODE_START + n

    code_end = CODE_START + ALLOCATED_NUMBER - 1  # 此时为 10030
    # 如果是当期最后一个号码，则进入开奖逻辑
    if code == code_end:
        # 预生成下一期的参与号码以保持平衡
        preallocate_codes()
        # 进入开奖过程
        open_lottery(period)
```

# 开奖服务

计算对应期数开奖结果并写入数据库

```python
def open_lottery(period):
    """计算对应期数开奖结果并写入数据库"""
    # 获取对应期数所有用户的时间累加值
    period_cumulative_time_key = PERIOD_CUMULATIVE_TIME.format(period)  # 初始化对应期数累加时间的 key
    cumulative_time = int(redis.get(period_cumulative_time_key))

    # 根据时间累加值求余数, 用于计算中奖号码和获取中奖用户
    winner_mod = cumulative_time % 30

    # 根据余数计算中奖号码
    winner_code = CODE_START + winner_mod

    # 从缓存的参与用户列表中获取中奖用户
    period_involved_users_key = PERIOD_INVOLVED_USERS.format(period)  # 初始化对应期数保存参与用户的 key
    winner_uid = redis.lindex(period_involved_users_key, winner_mod)

    # 删除 redis 缓存的当期时间累加值和参与用户列表
    redis.delete(period_cumulative_time_key, period_involved_users_key)
    # 更新 free_meals 表对应的中奖用户、中奖号码、以及开奖时间和状态
    update_free_meals_period_set_winner(period=period, winner_uid=winner_uid, winner_code=winner_code)
```

### 模拟实现

花了一点时间用 `flask` 把上面的逻辑实现了下, 毕竟编程在于实践。 主要基于伪代码稍微修改了下, 所以结构有点乱。

* 使用 `dataset` 和 `fakeredis` 来 `mock` 数据库和 `redis`
* 为了方便每期默认号码数由 `20` 改为 `3`
* 预分配 `2` 期号码池

并在过程中会把相关数据库和  `redis` 的情况都打印出来, 方便理解

[example.py](./example.py) 是 `server` 端，[test.py](./test.py) 是 `client` 端

#### 运行

#### 安装依赖

`pip install -r requirements.txt`

#### 运行服务器

`python example.py`


#### 运行测试

`python test.py`

####  分析结果如下

* 首先服务启动后初始化两期中奖号码池到队列中。

* 当 `uid` 为 `1` 的用户请求号码时，从队列中取出一个号码给他。因为是第一期的第一个号码，所以在 `free_meals` 里面插入一条记录, 在 `free_meal_details` 里面插入对应获取的号码

![](https://raw.githubusercontent.com/shidenggui/assets/master/algorithm/architecture/free_meals/test_result_1-min.png)

* 当 `uid` 为 `2` 的用户请求号码时，从队列中取出一个号码。在 `free_meal_details` 里面插入对应获取的号码。

![](https://raw.githubusercontent.com/shidenggui/assets/master/algorithm/architecture/free_meals/test_result_2-min.png)

* 当 `uid` 为 `3` 的用户请求号码时，从队列中取出一个号码。在 `free_meal_details` 里面插入对应获取的号码。同时因为 10003 已经是我们设置分配的最后一个号码，所以触发预分配和开奖流程。使队列中还是保持`2`期的号码池

![](https://raw.githubusercontent.com/shidenggui/assets/master/algorithm/architecture/free_meals/test_result_3-min.png)

* 当 `uid` 为 `4` 的用户请求号码时，参考 `uid` 用户为 `1` 的过程

![](https://raw.githubusercontent.com/shidenggui/assets/master/algorithm/architecture/free_meals/test_result_4-min.png)
