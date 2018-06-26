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
        channel = Object('com.qianmi.pc.base.api.constants.ChannelEnum', values={
            'name': 'D2C'
        })

        spu_query_request = Object('com.qianmi.pc.item.api.spu.request.SpuQueryRequest')
        spu_query_request['chainMasterId'] = 'A000000'
        spu_query_request['channel'] = channel
        spu_query_request['pageSize'] = 20
        result = self.spu_query_provider.call('query', spu_query_request)
        # pretty_print(result)
        total = result['totalCount']
        print total
        print len(result['dataList'])

        data_list = result['dataList']
        for data in data_list:
            spu_id = data['spuId']
            spu_desc_request = Object('com.qianmi.pc.item.api.spu.request.SpuDescriptionGetRequest')
            spu_desc_request['spuId'] = spu_id
            print spu_id
            spu_desc_request['chainMasterId'] = 'A000000'
            pretty_print(self.spu_query_provider.call('getDescription', spu_desc_request))

        for data in data_list:
            spu_request = Object('com.qianmi.pc.item.api.spu.request.SpuGetRequest')
            spu_request['chainMasterId'] = 'A000000'
            spu_request['spuId'] = data['spuId']
            spu_request['channelEnum'] = channel

            pretty_print(self.spu_query_provider.call('getById', spu_request))

        spu_ids = map(lambda spu: spu['spuId'], data_list)
        spu_ids_request = Object('com.qianmi.pc.item.api.spu.request.SpuListByIdsRequest')
        spu_ids_request['chainMasterId'] = 'A000000'
        spu_ids_request['channelEnum'] = channel
        spu_ids_request['spuIds'] = spu_ids
        batch_spu_request = self.spu_query_provider.call('listByIds', spu_ids_request)
        pretty_print(batch_spu_request)


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in range(100000):
        _dubbo.call('echo18')


if __name__ == '__main__':
    unittest.main()
