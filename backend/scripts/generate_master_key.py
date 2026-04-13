import base64
import os


if __name__ == '__main__':
    key = base64.b64encode(os.urandom(32)).decode('utf-8')
    print(key)
