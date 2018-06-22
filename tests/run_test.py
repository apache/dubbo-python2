# -*- coding: utf-8 -*-
import json
import unittest

from dubbo.client import DubboClient, ZkRegister
from dubbo.codec.encoder import Object
from dubbo.common.loggers import init_log


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

        # zk = ZkRegister('172.21.4.98:2181')
        # self.dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
        self.dubbo = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')

    def test_run(self):
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
        lock['lockReason'] = '加锁的原因是什么呢？'
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

        # print dubbo.call('echo', ['张老师', '三', 19, 2000.0, True])
        #
        # for i in range(10):
        #     thread = threading.Thread(target=run, args=(dubbo,))
        #     thread.start()


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in range(100000):
        _dubbo.call('echo18')


if __name__ == '__main__':
    unittest.main()
