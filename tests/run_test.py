# -*- coding: utf-8 -*-
import json
import threading
import unittest

import time

from dubbo.client import DubboClient, ZkRegister
from dubbo.codec.encoder import Object
from dubbo.common.loggers import init_log


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

    def test_run_default(self):
        zk = ZkRegister('172.19.71.7:2181')
        dubbo_cli = DubboClient('com.qianmi.pc.es.api.EsGoodsQueryProvider', zk_register=zk)

        goods_query_request = Object('com.qianmi.pc.es.api.request.EsGoodsQueryRequest', values={
            'chainMasterId': 'A859315',
            'fromSys': 2,
            'pageNum': 1
        })
        result = dubbo_cli.call('query', goods_query_request)
        pretty_print(result)

    @unittest.skip('skip not important test')
    def test_run(self):
        zk = ZkRegister('127.0.0.1:2181')
        dubbo_cli = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
        for i in xrange(4):
            thread = threading.Thread(target=run, args=(dubbo_cli,))
            thread.start()


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in xrange(1000):
        _dubbo.call('echo18')


if __name__ == '__main__':
    unittest.main()
