# -*- coding: utf-8 -*-
import re
import socket
from random import randint
from urllib import unquote

from kazoo.client import KazooClient

DUBBO_ZK_PROVIDERS = '/dubbo/{0}/providers'
PROVIDER_HOST_PATTERN = re.compile(r'dubbo://(?P<host>[\d\D]+?)/')


def parse_provider_host(provider):
    provider = unquote(provider)
    m = PROVIDER_HOST_PATTERN.match(provider)
    if m:
        host = m.group('host')
        ip, port = host.split(':')
        return Client(ip, int(port))
    raise ValueError('can\'t find provider host in [{0}]'.format(provider))


class ProvidersConnection(object):
    def __init__(self, hosts):
        zk = KazooClient(hosts=hosts)
        zk.start()

        self.zk = zk
        self.connections = {}

    def get_connection(self, interface):
        if self.connections.get(interface):
            providers = self.connections[interface]
        else:
            path = DUBBO_ZK_PROVIDERS.format(interface)
            if self.zk.exists(path):
                providers = self.zk.get_children(path)
                providers = map(parse_provider_host, providers)
                self.connections[interface] = providers
            else:
                raise Exception('can\'t providers for interface {0}'.format(interface))
        return providers[randint(0, len(providers) - 1)]

    def close(self):
        self.zk.stop()
        # 关闭所有与provider的连接
        for interface in self.connections.keys():
            providers = self.connections[interface]
            for provider in providers:
                provider.close()


class Client(object):
    def __init__(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        self.__sock = sock

    def write(self, data):
        self.__sock.sendall(data)

    def read(self, length):
        return bytearray(self.__sock.recv(length))

    def close(self):
        self.__sock.close()


connection = ProvidersConnection('127.0.0.1:2181')

if __name__ == '__main__':
    print connection.get_connection('me.hourui.echo.provider.Echo')
    print connection.get_connection('me.hourui.echo.provider.Echo')
