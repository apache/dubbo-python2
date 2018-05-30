# -*- coding: utf-8 -*-
import json

import time

import logging

from common.loggers import init_log
from connection.connections import ZkRegister, connection_pool

logger = logging.getLogger('dubbo.py')


class DubboClient(object):
    def __init__(self, interface, version='1.0.0', dubbo_version='2.4.10', zk_register=None, host=None):
        self.interface = interface
        self.version = version
        self.dubbo_version = dubbo_version

        self.zk_register = zk_register
        self.host = host

    def call(self, method, args=()):
        if self.zk_register:  # 优先从zk中获取provider的host
            host = self.zk_register.get_provider_host(self.interface)
        else:
            host = self.host
        logger.debug('get host {}'.format(host))

        request_param = {
            'dubbo_version': self.dubbo_version,
            'version': self.version,
            'path': self.interface,
            'method': method,
            'arguments': args
        }
        # logger.debug(request_param)
        result = connection_pool.get(host, request_param)
        return result


def pretty_print(value):
    logger.debug(json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True))


if __name__ == '__main__':
    init_log()  # 初始化日志配置，调用端需要自己配置日志属性

    zk = ZkRegister('127.0.0.1:2181')
    dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
    # dubbo = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')

    pretty_print(dubbo.call('echo', ['张老师', '三', 19, 2000.0, True]))
    pretty_print(dubbo.call('echo1', '昊天金阙无上至尊自然妙有弥罗至真高天上圣大慈仁者玉皇赦罪锡福大天尊玄穹高上帝'))
    pretty_print(dubbo.call('echo2', False))
    pretty_print(dubbo.call('echo3', [1000000000, 0x7ff, 100000, 10000]))
    pretty_print(dubbo.call('echo4', [1.00000004, 100000.0, 1.0, 2.0, 0.0]))
    assert 200 == dubbo.call('echo5', 200)
    assert 10000 == dubbo.call('echo5', 10000)

    assert 0.0 == dubbo.call('echo6', 0.0)
    assert 1.0 == dubbo.call('echo6', 1.0)
    assert 100.0 == dubbo.call('echo6', 100.0)
    assert 100000.0 == dubbo.call('echo6', 100000.0)

    assert 10000000000 == dubbo.call('echo7', 10000000000)
    assert 0 == dubbo.call('echo7', 0)
    assert 100 == dubbo.call('echo7', 100)
    assert 1000 == dubbo.call('echo7', 1000)
    assert 100000 == dubbo.call('echo7', 100000)

    pretty_print(dubbo.call('echo8'))
    pretty_print(dubbo.call('echo9'))
    pretty_print(dubbo.call('echo10'))
    pretty_print(dubbo.call('echo11'))
    pretty_print(dubbo.call('echo12'))
    pretty_print(dubbo.call('echo13'))
    pretty_print(dubbo.call('echo14'))
    pretty_print(dubbo.call('echo15'))
    pretty_print(dubbo.call('echo16'))
    pretty_print(dubbo.call('echo17'))

    log = logging.getLogger('dubbo.py')
    log.debug('1111')
    log.info('22222')
    time.sleep(1000)
