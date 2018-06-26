# -*- coding: utf-8 -*-
import json
import unittest

from dubbo.client import DubboClient, ZkRegister
from dubbo.codec.encoder import Object
from dubbo.common.loggers import init_log


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

        zk = ZkRegister('172.21.4.71:2181')
        self.spu_query_provider = DubboClient('com.qianmi.pc.item.api.spu.SpuQueryProvider', zk_register=zk)
        # self.dubbo = DubboClient('com.qianmi.pc.item.api.spu', host='172.21.36.82:20880')

    def test_run(self):
        # channel = Object('com.qianmi.pc.base.api.constants.ChannelEnum')
        # channel['name'] = 'D2C'
        #
        # spu_query_request = Object('com.qianmi.pc.item.api.spu.request.SpuQueryRequest')
        # spu_query_request['chainMasterId'] = 'A000000'
        # spu_query_request['channel'] = channel
        # spu_query_request['pageSize'] = 2000
        #
        # result = self.spu_query_provider.call('query', spu_query_request)
        # pretty_print(result)
        # print len(result['dataList'])

        dubbo_cli = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')
        dubbo_cli.call('echo11')


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in range(100000):
        _dubbo.call('echo18')


if __name__ == '__main__':
    unittest.main()
