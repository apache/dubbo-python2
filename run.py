# -*- coding: utf-8 -*-
import json
import threading

from common.loggers import init_log
from connection.connections import ZkRegister
from dubbo import DubboClient


def pretty_print(value):
    print json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True)


def run(_dubbo):
    for j in range(100000):
        _dubbo.call('echo18')


if __name__ == '__main__':
    init_log()  # 初始化日志配置，调用端需要自己配置日志属性

    zk = ZkRegister('172.19.65.33:2181')
    # dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)
    dubbo = DubboClient('me.hourui.echo.provider.Echo', host='127.0.0.1:20882')

    result = dubbo.call('echo17')
    pretty_print(result)

    # print dubbo.call('echo', ['张老师', '三', 19, 2000.0, True])
    #
    # for i in range(10):
    #     thread = threading.Thread(target=run, args=(dubbo,))
    #     thread.start()
