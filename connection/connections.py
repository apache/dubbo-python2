# -*- coding: utf-8 -*-
import socket
import threading
from random import randint
from urllib import unquote, quote

import time
from urlparse import urlparse, parse_qsl

from kazoo.client import KazooClient

from common.util import get_ip, get_pid

DUBBO_ZK_PROVIDERS = '/dubbo/{}/providers'
DUBBO_ZK_CONSUMERS = '/dubbo/{}/consumers'

# 根据远程host保存与此host相关的连接
connection_pool = {}


def scanning_invalid_connection():
    """
    清理已关闭的链接或超时的链接
    :return:
    """
    while 1:
        for key in connection_pool.keys():
            conn = connection_pool[key]
            if time.time() - conn.last_active > 10:
                conn.close()
            if conn.closed:
                print 'close connection to remote host {}'.format(key)
                del connection_pool[key]
        time.sleep(5)


# thread = threading.Thread(target=scanning_invalid_connection)
# thread.start()


def get_provider_connection(host):
    """
    通过host获取到与此host相关的socket，本地会对socket进行缓存
    :param host:
    :return:
    """
    if not host or ':' not in host:
        raise ValueError('invalid host {}'.format(host))
    if not connection_pool.get(host):
        ip, port = host.split(':')
        connection_pool[host] = Connection(ip, int(port))
    return connection_pool[host]


class ZkRegister(object):
    """
    ZkRegister的主要作用：
    1. 根据特定的interface从zk中取出与之相关的所有provider的host并且监听
       provider的变化，当发生变化时更新最新的hosts到本地缓存；
    2. 当从zk中获取指定的interface的provider的时候，把当前进程作为此interface
       的一个consumer注册到zk中，并设置此节点的状态为ephemeral；
    """

    def __init__(self, hosts, application_name='search_platform'):
        zk = KazooClient(hosts=hosts)
        zk.start()

        self.zk = zk
        self.hosts = {}
        self.application_name = application_name

    def get_provider_host(self, interface):
        """
        从zk中可以根据接口名称获取到此接口某个provider的host
        :param interface:
        :return:
        """
        if not self.hosts.get(interface):
            path = DUBBO_ZK_PROVIDERS.format(interface)
            if self.zk.exists(path):
                providers = self.zk.get_children(path, watch=self._watch_children)
                if len(providers) == 0:
                    raise Exception('no providers for interface {}'.format(interface))
                providers = map(parse_url, providers)

                self._register_consumer(providers)
                self.hosts[interface] = map(lambda provider: provider['host'], providers)
            else:
                raise Exception('can\'t providers for interface {0}'.format(interface))
        hosts = self.hosts[interface]
        return hosts[randint(0, len(hosts) - 1)]

    def _watch_children(self, event):
        """
        对某个provider下的子节点进行监听，一旦provider发生了变化则对本地缓存进行更新
        :param event:
        :return:
        """
        path = event.path
        interface = path.split('/')[2]

        # 非常的古怪因为children的watch好像只会生效一次所以需要反复的重新设置watch
        providers = self.zk.get_children(path, watch=self._watch_children)
        if len(providers) == 0:
            raise Exception('no providers for interface {}'.format(interface))
        providers = map(parse_url, providers)
        self.hosts[interface] = map(lambda provider: provider['host'], providers)

    def _register_consumer(self, providers):
        """
        把本机注册到对应的interface的consumer上去
        :param providers:
        :return:
        """
        provider = providers[0]
        provider_fields = provider['fields']

        consumer = 'consumer://' + get_ip() + provider['path'] + '?'
        fields = {
            'application': self.application_name,
            'category': 'consumers',
            'check': 'false',
            'connected': 'true',
            'dubbo': provider_fields['dubbo'],
            'interface': provider_fields['interface'],
            'methods': provider_fields['methods'],
            'pid': get_pid(),
            'revision': provider_fields['revision'],
            'side': 'consumer',
            'timestamp': int(time.time() * 1000),
            'version': provider_fields['version'],
        }

        keys = fields.keys()
        keys.sort()
        for key in keys:
            value = fields[key]
            consumer += '{0}={1}&'.format(key, value)
        consumer = consumer[:-1]  # 干掉最后一个&

        consumer_path = DUBBO_ZK_CONSUMERS.format(fields['interface'])
        self.zk.ensure_path(consumer_path)
        self.zk.create(consumer_path + '/' + quote(consumer, safe=''), ephemeral=True)

    def close(self):
        self.zk.stop()


class Connection(object):
    """
    对Socket链接做了一些封装
    """

    def __init__(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        self.__sock = sock

        self.last_active = time.time()
        self.closed = False

    def write(self, data):
        self.last_active = time.time()
        self.__sock.sendall(data)

    def read(self, length):
        self.last_active = time.time()
        return bytearray(self.__sock.recv(length))

    def close(self):
        self.closed = True
        self.__sock.close()


def parse_url(url_str):
    """
    把url字符串解析为适合于操作的对象
    :param url_str:
    :return:
    """
    url = urlparse(unquote(url_str))
    fields = dict(parse_qsl(url.query))
    result = {
        'scheme': url.scheme,
        'host': url.netloc,
        'hostname': url.hostname,
        'port': url.port,
        'path': url.path,
        'fields': fields
    }
    return result


if __name__ == '__main__':
    pass
