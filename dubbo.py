# -*- coding: utf-8 -*-
import logging

from connection.connections import connection_pool

logger = logging.getLogger('dubbo.py')


class DubboClient(object):
    """
    用于实现dubbo调用的客户端
    """

    def __init__(self, interface, version='1.0.0', dubbo_version='2.4.10', zk_register=None, host=None):
        """
        :param interface: 接口名，例如：com.qianmi.pc.es.api.EsProductQueryProvider
        :param version: 接口的版本号，例如：1.0.0，默认为1.0.0
        :param dubbo_version: dubbo的版本号，默认为2.4.10
        :param zk_register: zookeeper注册中心管理端，参见类：ZkRegister
        :param host: 远程主机地址，用于绕过zookeeper进行直连，例如：172.21.4.98:20882
        """
        self.__interface = interface
        self.__version = version
        self.__dubbo_version = dubbo_version

        self.__zk_register = zk_register
        self.__host = host

    def call(self, method, args=(), timeout=None):
        """
        执行远程调用
        :param method: 远程调用的方法名
        :param args: 方法参数
                    1. 对于没有参数的方法，此参数不填；
                    2. 对于只有一个参数的方法，直接填入该参数；
                    3. 对于有多个参数的方法，传入一个包含了所有参数的列表；
        :param timeout: 请求超时时间（秒），不设置则不会超时。默认不设置，如无特殊需求不建议设置
                    * 不设置超时时间在某些极限情况下可能导致此连接一直阻塞；
                    * 设置超时时间会增加远程调用的时间；
        :return:
        """
        if not isinstance(args, (list, tuple)):
            args = [args]

        if self.__zk_register:  # 优先从zk中获取provider的host
            host = self.__zk_register.get_provider_host(self.__interface)
        else:
            host = self.__host
        # logger.debug('get host {}'.format(host))

        request_param = {
            'dubbo_version': self.__dubbo_version,
            'version': self.__version,
            'path': self.__interface,
            'method': method,
            'arguments': args
        }
        # logger.debug(request_param)
        result = connection_pool.get(host, request_param, timeout)
        return result


if __name__ == '__main__':
    pass
