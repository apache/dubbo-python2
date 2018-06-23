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
        print self.dubbo.call('test2', u'🐶🐶🐶111🐶🐶🐶你好啊啊🐶🐶🐶🐶の🐶🐶🐶🐶')

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
