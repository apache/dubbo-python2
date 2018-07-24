# -*- coding: utf-8 -*-
import json
import logging
import threading
import unittest

from dubbo.codec.encoder import Object
from dubbo.common.loggers import init_log
from dubbo.common.exceptions import DubboException
from dubbo.client import DubboClient, ZkRegister

logger = logging.getLogger('python-dubbo')


def pretty_print(value):
    logger.debug(json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True))


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

        zk = ZkRegister('127.0.0.1:2181')
        self.dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
        # self.dubbo = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')

    def tearDown(self):
        # Do something to clear the test environment here.
        pass

    # @unittest.skip('skip base test')
    def test(self):
        dubbo = self.dubbo

        pretty_print(dubbo.call('echo', ['张老师', '三', 19, 2000.0, True]))
        pretty_print(dubbo.call('echo1', '昊天金阙无上至尊自然妙有弥罗至真高天上圣大慈仁者玉皇赦罪锡福大天尊玄穹高上帝'))
        pretty_print(dubbo.call('echo2', False))
        pretty_print(dubbo.call('echo3', [1000000000, 0x7ff, 100000, 10000]))
        pretty_print(dubbo.call('echo4', [1.00000004, 100000.0, 1.0, 2.0, 0.0]))
        self.assertEquals('🐶', dubbo.call('echo1', '🐶'))
        self.assertEquals(200, dubbo.call('echo5', 200))
        self.assertEquals(10000, dubbo.call('echo5', 10000))

        self.assertEquals(0.0, dubbo.call('echo6', 0.0))
        self.assertEquals(1.0, dubbo.call('echo6', 1.0))
        self.assertEquals(100.0, dubbo.call('echo6', 100.0))
        self.assertEquals(100000.0, dubbo.call('echo6', 100000.0))

        self.assertEquals(10000000000, dubbo.call('echo7', 10000000000))
        self.assertEquals(0, dubbo.call('echo7', 0))
        self.assertEquals(100, dubbo.call('echo7', 100))
        self.assertEquals(1000, dubbo.call('echo7', 1000))
        self.assertEquals(100000, dubbo.call('echo7', 100000))

        pretty_print(dubbo.call('echo8'))
        pretty_print(dubbo.call('echo9'))
        pretty_print(dubbo.call('echo10'))
        pretty_print(dubbo.call('echo11'))
        pretty_print(dubbo.call('echo12'))
        pretty_print(dubbo.call('echo13'))
        pretty_print(dubbo.call('echo14'))
        pretty_print(dubbo.call('echo15'))
        pretty_print(dubbo.call('echo16'))

        with self.assertRaises(DubboException) as context:
            pretty_print(dubbo.call('echo17'))
            self.assertTrue('This is broken' in context.exception)

        pretty_print(dubbo.call('echo1', 'hello'))
        pretty_print(dubbo.call('echo18'))
        pretty_print(dubbo.call('echo19'))
        pretty_print(dubbo.call('echo20'))
        pretty_print(dubbo.call('echo21'))
        pretty_print(dubbo.call('echo22'))
        pretty_print(dubbo.call('echo23'))

        log = logging.getLogger('python-dubbo')
        log.debug('1111')
        log.info('22222')

    def _run_num(self):
        dubbo = self.dubbo

        self.assertEquals(-200, dubbo.call('echo5', -200))
        self.assertEquals(-10000, dubbo.call('echo5', -10000))
        self.assertEquals(200, dubbo.call('echo5', 200))
        self.assertEquals(10000, dubbo.call('echo5', 10000))

        self.assertEquals(0.0, dubbo.call('echo6', 0.0))
        self.assertEquals(1.0, dubbo.call('echo6', 1.0))
        self.assertEquals(100.0, dubbo.call('echo6', 100.0))
        self.assertEquals(100000.0, dubbo.call('echo6', 100000.0))

        self.assertEquals(10000000000, dubbo.call('echo7', 10000000000))
        self.assertEquals(0, dubbo.call('echo7', 0))
        self.assertEquals(100, dubbo.call('echo7', 100))
        self.assertEquals(1000, dubbo.call('echo7', 1000))
        self.assertEquals(100000, dubbo.call('echo7', 100000))

        self.assertEquals(3.1415926, dubbo.call('echo6', 3.1415926))

        self.assertEquals(-1.0, dubbo.call('echo6', -1.0))
        self.assertEquals(-100.0, dubbo.call('echo6', -100.0))
        self.assertEquals(-100000.0, dubbo.call('echo6', -100000.0))

        self.assertEquals(-10000000000, dubbo.call('echo7', -10000000000))
        self.assertEquals(-100, dubbo.call('echo7', -100))
        self.assertEquals(-1000, dubbo.call('echo7', -1000))
        self.assertEquals(-100000, dubbo.call('echo7', -100000))

    # @unittest.skip('skip performance test')
    def test_multi_threading(self):
        for i in xrange(10):
            thread = threading.Thread(target=self._run_num)
            thread.start()

    # @unittest.skip('skip performance test')
    def test_performance(self):
        for i in xrange(10):
            self.dubbo.call('echo18')

    def test_auto_rule(self):
        dubbo_cli = DubboClient('com.qianmi.common.autorule.api.WarehouseProvider', host='172.21.36.82:20880')
        delivery_man_query = Object('com.qianmi.common.autorule.api.request.warehouse.DeliveryManQueryRequest')
        delivery_man_query['userId'] = 'A1035712'
        delivery_man_query['warehouseId'] = '15373'
        delivery_man_query['deliveryManId'] = 'E132862'
        result = dubbo_cli.call('getWarehouseByDeliveryMan', delivery_man_query)
        pretty_print(result)

        delivery_area_query = Object('com.qianmi.common.autorule.api.request.warehouse.DeliveryAreaQueryRequest')
        delivery_area_query['userId'] = 'A1035527'
        delivery_area_query['warehouseId'] = '15346'
        delivery_area = Object('com.qianmi.common.autorule.api.bean.DeliveryArea')
        delivery_area['provinceName'] = '上海'
        delivery_area_query['deliveryArea'] = delivery_area

        result = dubbo_cli.call('getWarehouseByDeliveryArea', delivery_area_query)
        pretty_print(result)

        warehouse_type_request = Object('com.qianmi.common.autorule.api.request.warehouse.GetWarehouseRuleTypeRequest')
        warehouse_type_request['userId'] = 'A1035527'
        warehouse_type_request['warehouseId'] = '15346'
        result = dubbo_cli.call('getWarehouseRuleType', warehouse_type_request)
        pretty_print(result)

        zk_cli = ZkRegister('172.21.4.71:2181')
        dubbo_cli = DubboClient('com.qianmi.common.autorule.api.OrderRuleProvider', zk_register=zk_cli)
        order_query = Object('com.qianmi.common.autorule.api.request.order.OrderListByCustomerServiceIdRequest')
        order_query['userId'] = 'A1035527'
        order_query['customerServiceId'] = 'E132802'
        result = dubbo_cli.call('listOrdersByCustomerServiceId', order_query)
        pretty_print(result)

    @unittest.skip('object')
    def test_object(self):
        new_user = Object('me.hourui.echo.bean.NewUser')
        user1 = Object('me.hourui.echo.bean.User1')
        user2 = Object('me.hourui.echo.bean.User2')
        user3 = Object('me.hourui.echo.bean.User3')
        user4 = Object('me.hourui.echo.bean.User4')
        user5 = Object('me.hourui.echo.bean.User5')
        user6 = Object('me.hourui.echo.bean.User6')
        user7 = Object('me.hourui.echo.bean.User7')
        user8 = Object('me.hourui.echo.bean.User8')
        user9 = Object('me.hourui.echo.bean.User9')
        user10 = Object('me.hourui.echo.bean.User10')
        user11 = Object('me.hourui.echo.bean.User11')
        user12 = Object('me.hourui.echo.bean.User12')
        user13 = Object('me.hourui.echo.bean.User13')

        location = Object('me.hourui.echo.bean.Location')
        location['province'] = '江苏省'
        location['city'] = '南京市'
        location['street'] = '软件大道'

        name = Object('me.hourui.echo.bean.Name')
        name['firstName'] = '隔壁的'
        name['lastName'] = '王叔叔'

        employee = Object('me.hourui.echo.bean.retail.Employee')
        employee['id'] = 'A137639'
        employee['name'] = '我勒个去居然不能用emoji啊'

        lock = Object('me.hourui.echo.bean.retail.Lock')
        lock['lockReason'] = '加锁的原因是什么呢？🤔'
        lock['employee'] = employee
        lock['locked'] = True

        new_user['user1'] = user1
        new_user['user2'] = user2
        new_user['user3'] = user3
        new_user['user4'] = user4
        new_user['user5'] = user5
        new_user['user6'] = user6
        new_user['user7'] = user7
        new_user['user8'] = user8
        new_user['user9'] = user9
        new_user['user10'] = user10
        new_user['user11'] = user11
        new_user['user12'] = user12
        new_user['user13'] = user13
        new_user['location'] = location
        new_user['name'] = name
        new_user['lock'] = lock

        result = self.dubbo.call('test1', [new_user, name, '一个傻傻的用于测试的字符串', location, lock])
        # result = dubbo.call('echo23')
        pretty_print(result)

    def test_array(self):
        location1 = Object('me.hourui.echo.bean.Location')
        location1['province'] = '江苏省'
        location1['city'] = '南京市'
        location1['street'] = '软件大道'
        location2 = Object('me.hourui.echo.bean.Location')
        location2['province'] = '浙江省'
        location2['city'] = '杭州市'
        location2['street'] = '余杭区'

        user1 = Object('me.hourui.echo.bean.User1')
        user1['name'] = '张三'
        user2 = Object('me.hourui.echo.bean.User1')
        user2['name'] = '李四'

        array = Object('me.hourui.echo.bean.Object4Array')
        array['locations'] = [location1, location2]
        array['users'] = [user1, user2]
        array['strings'] = ['这是', '一个', '不可', '重复', '重复', '重复', '重复', '的', '列表']

        dubbo_cli = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')
        dubbo_cli.call('test4', [['你好', '我好'], [2, 3, 3, 3], array])

    def test_pc(self):
        zk = ZkRegister('172.21.4.71:2181')
        spu_query_provider = DubboClient('com.qianmi.pc.item.api.spu.SpuQueryProvider', zk_register=zk)

        channel = Object('com.qianmi.pc.base.api.constants.ChannelEnum', values={
            'name': 'D2C'
        })

        spu_query_request = Object('com.qianmi.pc.item.api.spu.request.SpuQueryRequest')
        spu_query_request['chainMasterId'] = 'A000000'
        spu_query_request['channel'] = channel
        spu_query_request['pageSize'] = 20
        result = spu_query_provider.call('query', spu_query_request)
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
            pretty_print(spu_query_provider.call('getDescription', spu_desc_request))

        for data in data_list:
            spu_request = Object('com.qianmi.pc.item.api.spu.request.SpuGetRequest')
            spu_request['chainMasterId'] = 'A000000'
            spu_request['spuId'] = data['spuId']
            spu_request['channelEnum'] = channel

            pretty_print(spu_query_provider.call('getById', spu_request))

        spu_ids = map(lambda spu: spu['spuId'], data_list)
        spu_ids_request = Object('com.qianmi.pc.item.api.spu.request.SpuListByIdsRequest')
        spu_ids_request['chainMasterId'] = 'A000000'
        spu_ids_request['channelEnum'] = channel
        spu_ids_request['spuIds'] = spu_ids
        batch_spu_request = spu_query_provider.call('listByIds', spu_ids_request)
        pretty_print(batch_spu_request)

    def test_pc_es_center(self):
        zk = ZkRegister('172.19.71.7:2181')
        dubbo_cli = DubboClient('com.qianmi.pc.es.api.EsGoodsQueryProvider', zk_register=zk)

        goods_query_request = Object('com.qianmi.pc.es.api.request.EsGoodsQueryRequest', values={
            'chainMasterId': 'A859315',
            'fromSys': 2,
            'pageNum': 50
        })
        result = dubbo_cli.call('query', goods_query_request)
        pretty_print(result)

        goods_list_by_id_request = Object('com.qianmi.pc.es.api.request.EsGoodsListByIdStringRequest', values={
            'chainMasterId': 'A859315',
            'idString': 'g51426:g51422'
        })
        result = dubbo_cli.call('listByIdString', goods_list_by_id_request)
        pretty_print(result)

        product_request = Object('com.qianmi.pc.es.api.request.EsGoodsListByIdStringRequest', values={
            'chainMasterId': 'A000000',
            'idString': 'NotUsed:g10529'
        })
        result = dubbo_cli.call('listByIdString', product_request)
        pretty_print(result)


if __name__ == '__main__':
    # test = TestDubbo()
    # test.setUp()
    # test.test_performance()
    unittest.main()
