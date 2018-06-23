# python-dubbo

_Python Dubbo Client._

## Installation

    pip install python-dubbo

## Example


## Reference

* Python字节相关的转化操作：<https://docs.python.org/2/library/struct.html>
* Hessian2的编码规则：<http://hessian.caucho.com/doc/hessian-serialization.html>
* 实现Hessian2编码时的参考：[参考1](https://github.com/WKPlus/pyhessian2/blob/3.1.5/pyhessian2/encoder.py)，[参考2](https://github.com/zhouyougit/PyDubbo/blob/master/dubbo/hessian2.py)
* Dubbo相关的编码规则：[参考1](http://fe.58qf.com/2017/11/07/node-dubbo/)，[参考2](http://cxis.me/2017/03/19/Dubbo%E4%B8%AD%E7%BC%96%E7%A0%81%E5%92%8C%E8%A7%A3%E7%A0%81%E7%9A%84%E8%A7%A3%E6%9E%90/)
* Dubbo的心跳机制：<http://www.cnblogs.com/java-zhao/p/8539046.html>
* 部分实现参考了dubbo的Java源码中的实现
* 对于所有的字符串，在网络传输前进行编码，编码一律使用unicode来完成，如果一个字符串是str则先将其decode为unicode之后再进行操作；
* 对于所有的字符串，在网络上获取到的数据之后进行解码，解码得到的字符串是unicode，之后将其encode为str再交给客户程序；
* 支持传输utf-8编码和Emoji🧐