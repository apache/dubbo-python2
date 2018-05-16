# -*- coding: utf-8 -*-
from codec.decoder import get_response_body_length
from codec.encoder import encode
from connection.connections import Client

client = Client('127.0.0.1', 20880)


def call(dubbo_version='2.4.10',
         version='1.0.0',
         path=None,
         method=None,
         arguments=None):
    request_param = {
        'dubbo_version': dubbo_version,
        'version': version,
        'path': path,
        'method': method,
        'arguments': arguments
    }
    request = encode(request_param)
    client.write(request)
    response_head = client.read(16)
    response_body_length = get_response_body_length(response_head)
    response_body = client.read(response_body_length)
    print response_body


if __name__ == '__main__':
    call(
        path='me.hourui.echo.provider.Echo',
        method='echo',
        arguments=['张', '三', 19, 2000.0, True]
    )
