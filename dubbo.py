# -*- coding: utf-8 -*-
import json

from codec.decoder import get_response_body_length, Response
from codec.encoder import encode
from connection.connections import Client

client = Client('127.0.0.1', 20880)


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def call(dubbo_version='2.4.10', version='1.0.0', path=None, method=None, arguments=None):
    request_param = {
        'dubbo_version': dubbo_version,
        'version': version,
        'path': path,
        'method': method,
        'arguments': arguments
    }
    request = encode(request_param)
    client.write(request)

    # 响应数据的头部大小为16个字节
    response_head = client.read(16)
    response_body_length = get_response_body_length(response_head)

    response_body = client.read(response_body_length)
    client.close()
    res = Response(response_body)
    res.read_int()  # 响应的状态
    result = res.read_next()
    pretty_print(result)


if __name__ == '__main__':
    call(path='me.hourui.echo.provider.Echo', method='echo', arguments=['张老师', '三', 19, 2000.0, True])
