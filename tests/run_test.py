# -*- coding: utf-8 -*-
import json
import threading
import unittest

from dubbo.client import DubboClient, ZkRegister
from dubbo.codec.encoder import Object
from dubbo.common.loggers import init_log


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

        zk = ZkRegister('172.19.71.7:2181')
        self.dubbo = DubboClient('com.qianmi.pc.es.api.EsGoodsQueryProvider', zk_register=zk)

    def test_run(self):
        # for i in xrange(10):
        #     thread = threading.Thread(target=run, args=(self.dubbo,))
        #     thread.start()
        # goods_query_request = Object('com.qianmi.pc.es.api.request.EsGoodsQueryRequest', values={
        #     'chainMasterId': 'A859315',
        #     'fromSys': 2,
        #     'pageNum': 50
        # })
        # result = self.dubbo.call('query', goods_query_request)
        # pretty_print(result)
        # goods_list_by_id_request = Object('com.qianmi.pc.es.api.request.EsGoodsListByIdStringRequest', values={
        #     'chainMasterId': 'A859315',
        #     'idString': 'g51426:g51422'
        # })
        # result = self.dubbo.call('listByIdString', goods_list_by_id_request)
        # pretty_print(result)

        zk = ZkRegister('172.19.71.7:2181')
        dubbo_cli = DubboClient('com.qianmi.pc.es.api.EsProductQueryProvider', zk_register=zk)
        product_request = Object('com.qianmi.pc.es.api.request.EsProductListByIdStringRequest', values={
            'chainMasterId': 'A859315',
            'idString': 'p32839:g51422'
        })
        result = dubbo_cli.call('listByIdString', product_request)
        pretty_print(result)


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in xrange(1000):
        _dubbo.call('echo18', timeout=1)


if __name__ == '__main__':
    unittest.main()
