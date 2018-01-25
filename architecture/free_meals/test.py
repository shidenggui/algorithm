import requests

API = 'http://localhost:5000'


def main():
    for _ in range(2):
        preallocate_codes()

    for uid in range(1, 5):
        user_fetch_code(uid)


def preallocate_codes():
    requests.post('{}/preallocate_codes'.format(API))


def user_fetch_code(uid):
    requests.get('{}/pay_success_callback'.format(API),
                 params={'uid': uid})


if __name__ == '__main__':
    main()
