# -*- coding: utf-8 -*-
import json
import logging
import threading
import unittest

from dubbo.common.loggers import init_log
from dubbo.common.exceptions import DubboException
from dubbo.client import DubboClient, ZkRegister

logger = logging.getLogger('dubbo.py')


def pretty_print(value):
    logger.debug(json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True))


class TestDubbo(unittest.TestCase):
    def setUp(self):
        init_log()  # 初始化日志配置，调用端需要自己配置日志属性

        zk = ZkRegister('172.21.4.98:2181')
        self.dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
        # dubbo = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20880')

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

        log = logging.getLogger('dubbo.py')
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
        for i in range(10):
            thread = threading.Thread(target=self._run_num)
            thread.start()

    # @unittest.skip('skip performance test')
    def test_performance(self):
        for i in range(10):
            self.dubbo.call('echo18')


if __name__ == '__main__':
    # test = TestDubbo()
    # test.setUp()
    # test.test_performance()
    unittest.main()
