# -*- coding: utf-8 -*-
import logging
import select
import socket
import threading
import time
from struct import unpack

from dubbo.codec.encoder import Request
from dubbo.codec.decoder import Response, get_body_length
from dubbo.common.constants import CLI_HEARTBEAT_RES_HEAD, CLI_HEARTBEAT_TAIL, CLI_HEARTBEAT_REQ_HEAD
from dubbo.common.exceptions import DubboResponseException, DubboRequestTimeoutException
from dubbo.common.util import get_heartbeat_id

logger = logging.getLogger('dubbo')


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

    def get(self, host, request_param, timeout=None):
        conn = self._get_connection(host)
        request = Request(request_param).encode()

        conn.lock()
        try:
            conn.clear()
            conn.write(request)
            conn.wait(timeout)  # 等待数据读取完毕或超时
            if host not in self.results:
                raise DubboRequestTimeoutException(
                    'Socket(host=\'{}\'): Read timed out. (read timeout={})'.format(host, timeout))
            result = self.results.pop(host)
        finally:
            conn.unlock()

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
                logger.exception(e)
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
                logger.exception(e)
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


if hasattr(select, 'epoll'):
    connection_pool = EpollConnectionPool()
else:
    connection_pool = SelectConnectionPool()


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
        """
        向远程主机写数据
        :param data:
        :return:
        """
        self.last_active = time.time()
        self.__sock.sendall(data)

    def read(self, length):
        """
        读取远程主机的数据
        :param length:
        :return:
        """
        self.last_active = time.time()
        return bytearray(self.__sock.recv(length, socket.MSG_WAITALL))

    def close(self):
        """
        关闭连接
        :return:
        """
        self.__sock.shutdown(socket.SHUT_RDWR)
        self.__sock.close()

    def remote_host(self):
        return self.__host

    def lock(self):
        """
        对此连接加锁
        :return:
        """
        return self.__lock.acquire()

    def unlock(self):
        """
        对此连接解锁
        :return:
        """
        self.__lock.release()

    def clear(self):
        """
        在进行wait和notify之前先要进行初始化操作
        :return:
        """
        self.__event.clear()

    def wait(self, timeout=None):
        # 如果notify更早的发生，将导致is_set为True，此时不再需要wait
        if not self.__event.is_set():
            self.__event.wait(timeout)

    def notify(self):
        self.__event.set()

    def __enter__(self):
        return self.lock()

    def __exit__(self, *unused):
        self.unlock()

    def __repr__(self):
        return self.__host


if __name__ == '__main__':
    pass
