# -*- coding: utf-8 -*-
import socket
import threading
import traceback
from random import randint
from struct import unpack
from urllib import unquote, quote

import time
from urlparse import urlparse, parse_qsl

import logging

import select
from kazoo.client import KazooClient

from codec.decoder import Response, get_body_length
from codec.encoder import encode
from common.constants import CLI_HEARTBEAT_RES_HEAD, CLI_HEARTBEAT_TAIL, CLI_HEARTBEAT_REQ_HEAD
from common.exceptions import DubboException, RegisterException, DubboResponseException
from common.util import get_ip, get_pid, get_heartbeat_id, is_linux

DUBBO_ZK_PROVIDERS = '/dubbo/{}/providers'
DUBBO_ZK_CONSUMERS = '/dubbo/{}/consumers'
DUBBO_ZK_CONFIGURATORS = '/dubbo/{}/configurators'

logger = logging.getLogger('dubbo.py')


class BaseConnectionPool(object):
    def __init__(self):
        # 根据远程host保存与此host相关的连接
        self._connection_pool = {}
        # 用于在多个线程之间保存结果
        self.results = {}
        # 保存客户端已经发生超时的心跳次数
        self.client_heartbeats = {}
        # 创建连接的锁
        self.__conn_lock = threading.Lock()

        reading_thread = threading.Thread(target=self._read_from_server)
        reading_thread.setDaemon(True)  # 当主线程退出时此线程同时退出
        reading_thread.start()

        scanning_thread = threading.Thread(target=self._send_heartbeat)
        scanning_thread.setDaemon(True)
        scanning_thread.start()

    def get(self, host, request_param):
        conn = self._get_connection(host)
        request = encode(request_param)

        with conn:
            conn.write(request)
            conn.wait()
            result = self.results.pop(host)

        if isinstance(result, Exception):
            raise result

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
            self.__conn_lock.acquire()
            if host not in self._connection_pool:
                self.client_heartbeats[host] = 0
                self._new_connection(host)
            self.__conn_lock.release()
        return self._connection_pool[host]

    def _new_connection(self, host):
        """
        创建一个新的连接
        :param host:
        :return:
        """
        raise NotImplementedError()

    def _delete_connection(self, conn):
        """
        移除一个连接
        :param conn:
        :return:
        """
        raise NotImplementedError()

    def _read_from_server(self):
        """
        管理读取所有远程主机的数据
        :return:
        """
        raise NotImplementedError()

    def _read(self, conn):
        host = conn.remote_host()

        # 数据的头部大小为16个字节
        head = conn.read(16)
        if not head:  # 连接已关闭
            logger.debug('{} closed by remote server'.format(host))
            self._delete_connection(conn)
            return

        try:
            heartbeat, body_length = get_body_length(head)
        except DubboResponseException as e:
            body_length = unpack('!i', head[12:])[0]
            body = conn.read(body_length)
            res = Response(body)
            error = res.read_next()
            self.results[host] = DubboResponseException('\n{}\n{}'.format(e.message, error))
            conn.notify()
            return
        body = conn.read(body_length)

        # 远程主机发送的心跳请求数据包
        if heartbeat == 2:
            logger.debug('❤ request  -> {}'.format(conn.remote_host()))
            msg_id = head[4:12]
            heartbeat_response = CLI_HEARTBEAT_RES_HEAD + list(msg_id) + CLI_HEARTBEAT_TAIL
            conn.write(bytearray(heartbeat_response))
        # 远程主机发送的心跳响应数据包
        elif heartbeat == 1:
            logger.debug('❤ response -> {}'.format(conn.remote_host()))
            self.client_heartbeats[host] -= 1
        # 普通的数据包
        else:
            try:
                res = Response(body)
                flag = res.read_int()
                if flag == 2:  # 响应的值为NULL
                    self.results[host] = None
                elif flag == 1:  # 正常的响应值
                    result = res.read_next()
                    self.results[host] = result
                elif flag == 0:  # 异常的响应值
                    err = res.read_error()
                    error = '\n{cause}: {detailMessage}\n'.format(**err)
                    stack_trace = err['stackTrace']
                    for trace in stack_trace:
                        error += '	at {declaringClass}.{methodName}({fileName}:{lineNumber})\n'.format(**trace)
                    self.results[host] = DubboResponseException(error)
                else:
                    raise DubboResponseException("Unknown result flag, expect '0' '1' '2', get " + flag)
            except Exception as e:
                self.results[host] = e
            finally:
                conn.notify()  # 唤醒请求线程

    def _send_heartbeat(self):
        """
        客户端发送心跳消息
        :return:
        """
        while 1:
            starting = time.time()
            for host in self._connection_pool.keys():
                conn = self._connection_pool[host]
                if time.time() - conn.last_active > 60:
                    if self.client_heartbeats[host] >= 3:
                        self._delete_connection(conn)
                        conn.close()  # 客户端主动关闭连接
                        logger.debug('{} closed by client'.format(host))
                        continue
                    self.client_heartbeats[host] += 1
                    req = CLI_HEARTBEAT_REQ_HEAD + get_heartbeat_id() + CLI_HEARTBEAT_TAIL
                    conn.write(bytearray(req))
            ending = time.time()
            time_delta = ending - starting
            if time_delta < 10:
                time.sleep(10 - time_delta)


class EpollConnectionPool(BaseConnectionPool):
    """
    epoll模型只支持Linux及其发行版
    """

    def __init__(self):
        self.__fds = {}  # 文件描述符所对应的连接
        self.__epoll = select.epoll()
        BaseConnectionPool.__init__(self)

    def _read_from_server(self):
        while 1:
            events = self.__epoll.poll(1)
            for fd, event in events:
                if event & select.EPOLLIN:
                    conn = self.__fds[fd]
                    self._read(conn)

    def _new_connection(self, host):
        ip, port = host.split(':')
        conn = Connection(ip, int(port))
        self.__epoll.register(conn.fileno(), select.EPOLLIN)
        self.__fds[conn.fileno()] = conn

        self._connection_pool[host] = conn

    def _delete_connection(self, conn):
        self.__epoll.unregister(conn.fileno())
        host = conn.remote_host()
        del self._connection_pool[host]


class SelectConnectionPool(BaseConnectionPool):
    """
    select模型支持大多数的现代操作系统
    """

    def __init__(self):
        self.select_timeout = 0.5  # select模型超时时间
        BaseConnectionPool.__init__(self)

    def _read_from_server(self):
        while 1:
            try:
                conns = self._connection_pool.values()
                readable, writeable, exceptional = select.select(conns, [], [], self.select_timeout)
            except select.error as e:
                logger.error(e)
                break
            for conn in readable:
                self._read(conn)

    def _new_connection(self, host):
        ip, port = host.split(':')
        self._connection_pool[host] = Connection(ip, int(port))
        # 保证select模型已经开始监听最新加入的这个fd的读事件，否则可能会导致此fd读事件丢失
        time.sleep(self.select_timeout)

    def _delete_connection(self, conn):
        del self._connection_pool[conn.remote_host()]


if is_linux():
    connection_pool = EpollConnectionPool()
else:
    connection_pool = SelectConnectionPool()


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
                    raise RegisterException('no providers for interface {}'.format(interface))
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
                raise RegisterException('can\'t providers for interface {0}'.format(interface))
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

        raise RegisterException('error for finding [{}] host with weight.'.format(interface))

    def _watch_children(self, event):
        """
        对某个provider下的子节点进行监听，一旦provider发生了变化则对本地缓存进行更新
        :param event:
        :return:
        """
        path = event.path
        interface = path.split('/')[2]

        providers = self.zk.get_children(path, watch=self._watch_children)
        logger.debug('{} providers: {}'.format(interface, providers))
        if len(providers) == 0:
            logger.debug('no providers for interface {}'.format(interface))
            del self.hosts[interface]
            return
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
        self.zk.create_async(consumer_path + '/' + quote(consumer, safe=''), ephemeral=True)

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
        self.__lock = threading.Lock()
        # Event是Condition的简单实现版本
        self.__event = threading.Event()

        self.__host = '{0}:{1}'.format(host, port)
        self.last_active = time.time()

    def fileno(self):
        """
        https://stackoverflow.com/a/39328021/4614538
        :return:
        """
        return self.__sock.fileno()

    def write(self, data):
        self.last_active = time.time()
        self.__sock.sendall(data)

    def read(self, length):
        self.last_active = time.time()
        return bytearray(self.__sock.recv(length, socket.MSG_WAITALL))

    def close(self):
        self.__sock.shutdown(socket.SHUT_RDWR)
        self.__sock.close()

    def remote_host(self):
        return self.__host

    def lock(self):
        return self.__lock.acquire()

    def unlock(self):
        self.__lock.release()

    def wait(self):
        # 如果notify更早的发生，将导致is_set为True，此时不再需要wait
        if not self.__event.is_set():
            self.__event.wait()
        # 为下一次的操作做初始化
        self.__event.clear()

    def notify(self):
        self.__event.set()

    def __enter__(self):
        return self.lock()

    def __exit__(self, *unused):
        self.unlock()

    def __repr__(self):
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
