# -*- coding: utf-8 -*-
import socket
import threading
from random import randint
from urllib import unquote, quote

import time
from urlparse import urlparse, parse_qsl

import logging
from kazoo.client import KazooClient

from codec.decoder import Response, get_body_length
from codec.encoder import encode
from common.constants import CLI_HEARTBEAT_RES_HEAD, CLI_HEARTBEAT_TAIL, CLI_HEARTBEAT_REQ_HEAD
from common.util import get_ip, get_pid, get_heartbeat_id

DUBBO_ZK_PROVIDERS = '/dubbo/{}/providers'
DUBBO_ZK_CONSUMERS = '/dubbo/{}/consumers'
DUBBO_ZK_CONFIGURATORS = '/dubbo/{}/configurators'

logger = logging.getLogger('dubbo.py')


class ConnectionPool(object):
    def __init__(self):
        # 根据远程host保存与此host相关的连接
        self._connection_pool = {}
        # 用于在多个线程之间保存结果
        self.results = {}
        self.client_heartbeats = {}
        self.evt = threading.Event()

        threading.Timer(10, self._send_heartbeat).start()

    def get(self, host, request_param):
        conn = self._get_connection(host)

        request = encode(request_param)
        conn.write(request)
        while 1:
            self.evt.wait(10)
            self.evt.clear()
            if host in self.results:
                break

        result = self.results[host]
        del self.results[host]
        return result

    def _get_connection(self, host):
        """
        通过host获取到与此host相关的socket，本地会对socket进行缓存
        :param host:
        :return:
        """
        if not host or ':' not in host:
            raise ValueError('invalid host {}'.format(host))
        if host not in self._connection_pool:
            ip, port = host.split(':')
            self._connection_pool[host] = Connection(ip, int(port))
            self.client_heartbeats[host] = 0

            # 创建连接后开始异步的读取此连接的数据
            thread = threading.Thread(target=self._read, args=(host,))
            thread.start()
        return self._connection_pool[host]

    def _read(self, host):
        conn = self._get_connection(host)

        while 1:
            # 数据的头部大小为16个字节
            head = conn.read(16)
            if len(head) == 0:  # 连接已关闭
                logger.warn('{} closed'.format(host))
                break

            heartbeat, body_length = get_body_length(head)
            body = conn.read(body_length)

            # 远程主机发送的心跳请求数据包
            if heartbeat == 2:
                logger.debug('❤️ -> {}'.format(conn.remote_host()))
                msg_id = head[4:12]
                heartbeat_response = CLI_HEARTBEAT_RES_HEAD + list(msg_id) + CLI_HEARTBEAT_TAIL
                conn.write(bytearray(heartbeat_response))
            # 远程主机发送的心跳响应数据包
            elif heartbeat == 1:
                logger.debug('❤️ -> {}'.format(conn.remote_host()))
                self.client_heartbeats[host] -= 1
            # 普通的数据包
            else:
                res = Response(body)
                flag = res.read_int()
                if flag == 2:  # 响应的值为NULL
                    self.results[host] = None
                    self.evt.set()
                elif flag == 1:  # 正常的响应值
                    result = res.read_next()
                    self.results[host] = result
                    self.evt.set()
                elif flag == 0:  # 异常的响应值
                    error = res.read_next()
                    print error
                else:
                    raise Exception("Unknown result flag, expect '0' '1' '2', get " + flag)

    def _send_heartbeat(self):
        """
        客户端发送心跳消息
        :return:
        """
        # 这玩意每次只能执行一次，所以需要反复的重新设定任务
        threading.Timer(10, self._send_heartbeat).start()

        for host in self._connection_pool.keys():
            conn = self._connection_pool[host]
            if time.time() - conn.last_active > 60:
                if self.client_heartbeats[host] >= 3:
                    # 先关闭连接，等待下次请求使用连接时再次创建连接
                    conn.close()
                    del self._connection_pool[host]
                    continue
                self.client_heartbeats[host] += 1
                req = CLI_HEARTBEAT_REQ_HEAD + get_heartbeat_id() + CLI_HEARTBEAT_TAIL
                conn.write(bytearray(req))


connection_pool = ConnectionPool()


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
        self.weights = {}
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

                # 试图从配置中取出权重相关的信息
                configurators = self.zk.get_children(DUBBO_ZK_CONFIGURATORS.format(interface),
                                                     watch=self._watch_configurators)
                if configurators:
                    configurators = map(parse_url, configurators)
                    conf = {}
                    for configurator in configurators:
                        conf[configurator['host']] = configurator['fields'].get('weight', 100)  # 默认100
                    self.weights[interface] = conf
            else:
                raise Exception('can\'t providers for interface {0}'.format(interface))
        return self._routing_with_wight(interface)

    def _routing_with_wight(self, interface):
        """
        根据接口名称以及配置好的权重信息获取一个host
        :param interface:
        :return:
        """
        hosts = self.hosts[interface]
        # 此接口没有权重设置，使用朴素的路由算法
        if not self.weights.get(interface):
            return hosts[randint(0, len(hosts) - 1)]

        weights = self.weights[interface]
        hosts_weight = []
        for host in hosts:
            hosts_weight.append(int(weights.get(host, '100')))

        hit = randint(0, sum(hosts_weight) - 1)
        for i in range(len(hosts)):
            if hit <= sum(hosts_weight[:i + 1]):
                return hosts[i]

        raise Exception('error for finding [{}] host with weight.'.format(interface))

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

    def _watch_configurators(self, event):
        """
        监测某个interface中provider的权重的变化信息
        :param event:
        :return:
        """
        path = event.path
        interface = path.split('/')[2]

        # 试图从配置中取出权重相关的信息
        configurators = self.zk.get_children(DUBBO_ZK_CONFIGURATORS.format(interface),
                                             watch=self._watch_configurators)
        if configurators:
            configurators = map(parse_url, configurators)
            conf = {}
            for configurator in configurators:
                conf[configurator['host']] = configurator['fields'].get('weight', 100)
            self.weights[interface] = conf
        else:
            # 没有权重配置则意味着此配置可以被删除
            del self.weights[interface]

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

        self.__host = '{0}:{1}'.format(host, port)
        self.last_active = time.time()

    def write(self, data):
        self.last_active = time.time()
        self.__sock.sendall(data)

    def read(self, length):
        self.last_active = time.time()
        return bytearray(self.__sock.recv(length))

    def close(self):
        self.__sock.shutdown(socket.SHUT_RDWR)
        self.__sock.close()

    def remote_host(self):
        return self.__host


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
