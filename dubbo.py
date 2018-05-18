# -*- coding: utf-8 -*-
import json

from codec.decoder import get_response_body_length, Response
from codec.encoder import encode
from connection.connections import connection


class Dubbo(object):
    class _Method(object):
        def __init__(self, client_instance, method):
            self.client_instance = client_instance
            self.method = method

        def __call__(self, *args, **kwargs):
            return self.client_instance.call(self.method, *args, **kwargs)

    def __init__(self, interface, version='1.0.0', dubbo_version='2.4.10'):
        self.interface = interface
        self.version = version
        self.dubbo_version = dubbo_version

    def __getattr__(self, method, *args, **kwargs):
        return self._Method(client_instance=self, method=method)

    def call(self, method, *args, **kwargs):
        pass


dubbo = Dubbo('me.hourui.echo.provider.Echo')
dubbo.run(1, )


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def call(dubbo_version='2.4.10', version='1.0.0', path=None, method=None, arguments=()):
    client = connection.get_connection(path)

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
    return res.read_next()


if __name__ == '__main__':
    call(path='me.hourui.echo.provider.Echo', method='echo', arguments=['张老师', '三', 19, 2000.0, True])
    call(path='me.hourui.echo.provider.Echo', method='echo1', arguments='昊天金阙无上至尊自然妙有弥罗至真高天上圣大慈仁者玉皇赦罪锡福大天尊玄穹高上帝')
    call(path='me.hourui.echo.provider.Echo', method='echo2', arguments=False)
    call(path='me.hourui.echo.provider.Echo', method='echo3', arguments=[1000000000, 0x7ff, 100000, 10000])
    call(path='me.hourui.echo.provider.Echo', method='echo4', arguments=[1.00000004, 100000.0, 1.0, 2.0, 0.0])
    assert 200 == call(path='me.hourui.echo.provider.Echo', method='echo5', arguments=200)
    assert 10000 == call(path='me.hourui.echo.provider.Echo', method='echo5', arguments=10000)

    assert 0.0 == call(path='me.hourui.echo.provider.Echo', method='echo6', arguments=0.0)
    assert 1.0 == call(path='me.hourui.echo.provider.Echo', method='echo6', arguments=1.0)
    assert 100.0 == call(path='me.hourui.echo.provider.Echo', method='echo6', arguments=100.0)
    assert 100000.0 == call(path='me.hourui.echo.provider.Echo', method='echo6', arguments=100000.0)

    assert 10000000000 == call(path='me.hourui.echo.provider.Echo', method='echo7', arguments=10000000000)
    assert 0 == call(path='me.hourui.echo.provider.Echo', method='echo7', arguments=0)
    assert 100 == call(path='me.hourui.echo.provider.Echo', method='echo7', arguments=100)
    assert 1000 == call(path='me.hourui.echo.provider.Echo', method='echo7', arguments=1000)
    assert 100000 == call(path='me.hourui.echo.provider.Echo', method='echo7', arguments=100000)

    call(path='me.hourui.echo.provider.Echo', method='echo8')
    call(path='me.hourui.echo.provider.Echo', method='echo9')
    call(path='me.hourui.echo.provider.Echo', method='echo10')
    call(path='me.hourui.echo.provider.Echo', method='echo11')
    call(path='me.hourui.echo.provider.Echo', method='echo12')
    call(path='me.hourui.echo.provider.Echo', method='echo13')
    call(path='me.hourui.echo.provider.Echo', method='echo14')

    call(path='me.hourui.echo.provider.Echo', method='echo15')
    call(path='me.hourui.echo.provider.Echo', method='echo16')
