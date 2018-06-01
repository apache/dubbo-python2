# -*- coding: utf-8 -*-
from common.loggers import init_log
from connection.connections import ZkRegister
from dubbo import DubboClient

init_log()  # 初始化日志配置，调用端需要自己配置日志属性

zk = ZkRegister('127.0.0.1:2181')
dubbo = DubboClient('me.hourui.echo.provider.Echo', zk_register=zk)

print dubbo.call('echo', ['张老师', '三', 19, 2000.0, True])
for i in range(100000):
    dubbo.call('echo18')
