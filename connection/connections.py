# -*- coding: utf-8 -*-
import re
import socket
import threading
from random import randint
from urllib import unquote

import time
from kazoo.client import KazooClient

DUBBO_ZK_PROVIDERS = '/dubbo/{0}/providers'
PROVIDER_HOST_PATTERN = re.compile(r'dubbo://(?P<host>[\d\D]+?)/')

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


thread = threading.Thread(target=scanning_invalid_connection)
thread.start()


def get_provider_connection(host):
    """
    通过host获取到与此host相关的socket，本地会对socket进行缓存
    :param host:
    :return:
    """
    if not connection_pool.get(host):
        ip, port = host.split(':')
        connection_pool[host] = Connection(ip, int(port))
    return connection_pool[host]


class ZkRegister(object):
    def __init__(self, hosts):
        zk = KazooClient(hosts=hosts)
        zk.start()

        self.zk = zk
        self.hosts = {}

    def get_provider_host(self, interface):
        """
        从zk中可以根据接口名称获取到此接口某个provider的host
        :param interface:
        :return:
        """
        if not self.hosts.get(interface):
            path = DUBBO_ZK_PROVIDERS.format(interface)
            if self.zk.exists(path):
                providers = self.zk.get_children(path)
                self._register_consumer(providers)
                self.hosts[interface] = map(parse_provider_host, providers)
            else:
                raise Exception('can\'t providers for interface {0}'.format(interface))
        hosts = self.hosts[interface]
        return hosts[randint(0, len(hosts) - 1)]

    def _register_consumer(self, providers):
        pass

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


def parse_provider_host(provider):
    """
    从dubbo在zk中provider的信息中解析出此provider的host
    :param provider:
    :return:
    """
    provider = unquote(provider)
    m = PROVIDER_HOST_PATTERN.match(provider)
    if m:
        return m.group('host')
    raise ValueError('can\'t find provider host in [{0}]'.format(provider))
