# python-dubbo

_Python Dubbo Client._

## Installation

    pip install python-dubbo

## Usage

#### 基础使用

```python
from dubbo.client import DubboClient, ZkRegister

# 支持从Zk中获取服务的provider，支持根据provider的权重选择主机
zk = ZkRegister('127.0.0.1:2181')
dubbo_cli = DubboClient('com.qianmi.pc.api.GoodsQueryProvider', zk_register=zk)

# 支持不使用Zk，直接连接指定的远程主机
dubbo_cli = DubboClient('com.qianmi.pc.api.GoodsQueryProvider', host='127.0.0.1:20880')

admin_id = 'A000000'
result = dubbo_cli.call('listByIdString', admin_id)
```

#### 如何定义参数

python-dubbo支持以下Java类型的参数，表格右边一列代表了在Pyton中与指定Java类型所对应的类型

| 类型 | Java | Python |
| :--- | :--- | :--- |
| 布尔类型 | boolean | bool |
| 整型 | int, long | int |
| 浮点类型 | float, double | float |
| 字符串类型 | java.lang.String | str |
| 列表类型 | Collection & Array | [] |
| 自定义的对象类型 | java.lang.Object | ↓ _具体使用方法如下所示_ ↓ |

##### 使用Java的对象类型
```python
from dubbo.client import DubboClient, ZkRegister
from dubbo.codec.encoder import Object

# 创建channel对象
channel = Object('com.qianmi.pc.base.api.constants.ChannelEnum', values={
    'name': 'D2C'
})

# 创建spu_query_request对象
spu_query_request = Object('com.qianmi.pc.item.api.spu.request.SpuQueryRequest')
spu_query_request['chainMasterId'] = 'A000000'
spu_query_request['channel'] = channel
spu_query_request['pageSize'] = 2000

# 创建consumer并执行查询操作
zk = ZkRegister('172.21.4.71:2181')
spu_query_provider = DubboClient('com.qianmi.pc.item.api.spu.SpuQueryProvider', zk_register=zk)
result = spu_query_provider.call('query', spu_query_request)
```

#### 如何使用枚举(enum)类型作为参数

```python
# 定义一个枚举类型的对象
channel = Object('com.qianmi.pc.base.api.constants.ChannelEnum')
# 定义参数name并令其值为对应的枚举参数的值，之后使用该定义好的对象作为枚举类型变量即可
channel['name'] = 'D2C'
```

## Reference

* Python字节相关的转化操作：<https://docs.python.org/2/library/struct.html>
* Hessian2的编码规则：<http://hessian.caucho.com/doc/hessian-serialization.html>
* 实现Hessian2编码时的参考：[参考1](https://github.com/WKPlus/pyhessian2/blob/3.1.5/pyhessian2/encoder.py)，[参考2](https://github.com/zhouyougit/PyDubbo/blob/master/dubbo/hessian2.py)
* 对于部分不清楚且通过查阅文档仍无法了解的编码方式，先使用Java的dubbo客户端正常调用接口，之后使用[Wireshark](https://en.wikipedia.org/wiki/Wireshark)抓包获取请求和响应的数据报文，仔细的分析报文来推测编码方式
* Dubbo相关的编码规则：[参考1](http://fe.58qf.com/2017/11/07/node-dubbo/)，[参考2](http://cxis.me/2017/03/19/Dubbo%E4%B8%AD%E7%BC%96%E7%A0%81%E5%92%8C%E8%A7%A3%E7%A0%81%E7%9A%84%E8%A7%A3%E6%9E%90/)
* Dubbo的心跳机制：<http://www.cnblogs.com/java-zhao/p/8539046.html>
* 部分实现参考了dubbo的Java源码中的实现
* 对于所有的字符串，在网络传输前进行编码，编码一律使用unicode来完成，如果一个字符串是str则先将其decode为unicode之后再进行操作；
* 对于所有的字符串，在网络上获取到的数据之后进行解码，解码得到的字符串是unicode，之后将其encode为str再交给客户程序；
* 支持传输utf-8编码和Emoji😋
* 使用epoll模型来维护所有的链接，如果使用多线程来维护连接将产生过多的thread_context_switch，影响性能
* 类似于HTTP请求和响应，dubbo的请求和响应也是同步的并且可以看成是一个事务；不过dubbo使用了msg_id来为请求排序，这使得我们不再需要像HTTP请求那样在单个链接上进行同步的请求和响应，因此在单个连接上有多个请求时可以一定程度的降低请求总时间，这种对请求进行编码的理念类似于[HTTP2](https://zh.wikipedia.org/wiki/HTTP/2)中的stream ID
