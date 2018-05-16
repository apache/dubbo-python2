# -*- coding: utf-8 -*-
from codec.decoder import get_response_body_length, Response
from codec.encoder import encode
from connection.connections import Client

client = Client('127.0.0.1', 20880)


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
    res = Response(response_body)
    res.read_int()  # 响应的状态
    res.read_object()


if __name__ == '__main__':
    call(path='me.hourui.echo.provider.Echo', method='echo', arguments=['张爸爸', '三', 19, 2000.0, True])
