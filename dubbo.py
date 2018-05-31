# -*- coding: utf-8 -*-
import logging

from connection.connections import connection_pool

logger = logging.getLogger('dubbo.py')


class DubboClient(object):
    def __init__(self, interface, version='1.0.0', dubbo_version='2.4.10', zk_register=None, host=None):
        self.__interface = interface
        self.__version = version
        self.__dubbo_version = dubbo_version

        self.__zk_register = zk_register
        self.__host = host

    def call(self, method, args=()):
        if self.__zk_register:  # 优先从zk中获取provider的host
            host = self.__zk_register.get_provider_host(self.__interface)
        else:
            host = self.__host
        logger.debug('get host {}'.format(host))

        request_param = {
            'dubbo_version': self.__dubbo_version,
            'version': self.__version,
            'path': self.__interface,
            'method': method,
            'arguments': args
        }
        # logger.debug(request_param)
        result = connection_pool.get(host, request_param)
        return result


if __name__ == '__main__':
    pass
