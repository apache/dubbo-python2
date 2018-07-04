# -*- coding: utf-8 -*-
import logging
import select
import socket
import threading
import time
from struct import unpack, pack

from dubbo.codec.encoder import Request
from dubbo.codec.decoder import Response, parse_response_head
from dubbo.common.constants import CLI_HEARTBEAT_RES_HEAD, CLI_HEARTBEAT_TAIL, CLI_HEARTBEAT_REQ_HEAD, \
    TIMEOUT_CHECK_INTERVAL, TIMEOUT_IDLE, TIMEOUT_MAX_TIMES
from dubbo.common.exceptions import DubboResponseException, DubboRequestTimeoutException
from dubbo.common.util import get_invoke_id

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
        self.__events = {}

        reading_thread = threading.Thread(target=self._read_from_server)
        reading_thread.setDaemon(True)  # 当主线程退出时此线程同时退出
        reading_thread.start()

        scanning_thread = threading.Thread(target=self._send_heartbeat)
        scanning_thread.setDaemon(True)
        scanning_thread.start()

    def get(self, host, request_param, timeout=None):
        conn = self._get_connection(host)
        request = Request(request_param)
        request_data = request.encode()
        invoke_id = request.invoke_id

        event = threading.Event()
        self.__events[invoke_id] = event
        # 发送数据
        conn.write(request_data)
        event.wait(timeout)
        # 此event已经无效，应该删除
        del self.__events[invoke_id]
        result = self.results.pop(invoke_id)

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
            try:
                if host not in self._connection_pool:
                    self.client_heartbeats[host] = 0
                    self._new_connection(host)
            finally:
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
        """
        从指定的连接读取数据
        :param conn:
        :return:
        """
        host = conn.remote_host()

        # 数据的头部大小为16个字节
        head = conn.read(16)
        if not head:  # 连接已关闭
            logger.debug('{} closed by remote server'.format(host))
            self._delete_connection(conn)
            return

        try:
            heartbeat, body_length = parse_response_head(head)
        except DubboResponseException as e:  # 这里是dubbo的内部异常，与response中的业务异常不一样
            logger.exception(e)
            body_length = unpack('!i', head[12:])[0]
            body = conn.read(body_length)
            res = Response(body)
            error = res.read_next()
            invoke_id = unpack('!q', head[4:12])[0]
            self.results[invoke_id] = DubboResponseException('\n{}\n{}'.format(e.message, error))
            self.__events[invoke_id].set()
            return
        body = conn.read(body_length)
        self._parse_remote_data(head, body, heartbeat, conn, host)

    def _parse_remote_data(self, head, body, heartbeat, conn, host):
        """
        对从远程主机读取到的数据进行解析
        :param head:
        :param body:
        :param heartbeat:
        :param conn:
        :param host:
        :return:
        """
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
            self._parse_response(head, body)

    def _parse_response(self, head, body):
        """
        对dubbo的响应数据进行解析
        :param head:
        :param body:
        :return:
        """
        # 请求的调用id，目的是将请求和请求所对应的响应对应起来
        invoke_id = unpack('!q', head[4:12])[0]
        try:
            res = Response(body)
            flag = res.read_int()
            if flag == 2:  # 响应的值为NULL
                self.results[invoke_id] = None
            elif flag == 1:  # 正常的响应值
                result = res.read_next()
                self.results[invoke_id] = result
            elif flag == 0:  # 异常的响应值
                self.results[invoke_id] = self._parse_error(res)
            else:
                raise DubboResponseException("Unknown result flag, expect '0' '1' '2', get " + flag)
        except Exception as e:
            logger.exception(e)
            self.results[invoke_id] = e
        finally:
            self.__events[invoke_id].set()  # 唤醒请求线程

    @staticmethod
    def _parse_error(res):
        """
        对Java的异常错误信息进行解析
        :param res:
        :return:
        """
        err = res.read_error()
        error = '\n{cause}: {detailMessage}\n'.format(**err)
        stack_trace = err['stackTrace']
        for trace in stack_trace:
            error += '	at {declaringClass}.{methodName}({fileName}:{lineNumber})\n'.format(**trace)
        return DubboResponseException(error)

    def _send_heartbeat(self):
        """
        客户端发送心跳消息
        :return:
        """
        while 1:
            starting = time.time()
            for host in self._connection_pool.keys():
                conn = self._connection_pool[host]
                if time.time() - conn.last_active > TIMEOUT_IDLE:
                    if self.client_heartbeats[host] >= TIMEOUT_MAX_TIMES:
                        self._delete_connection(conn)
                        conn.close()  # 客户端主动关闭连接
                        logger.debug('{} closed by client'.format(host))
                        continue
                    self.client_heartbeats[host] += 1
                    invoke_id = list(bytearray(pack('!q', get_invoke_id())))
                    req = CLI_HEARTBEAT_REQ_HEAD + invoke_id + CLI_HEARTBEAT_TAIL
                    conn.write(bytearray(req))
            ending = time.time()
            time_delta = ending - starting
            if time_delta < TIMEOUT_CHECK_INTERVAL:
                time.sleep(TIMEOUT_CHECK_INTERVAL - time_delta)


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


# connection_pool在整个进程中是单例的
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

    def __repr__(self):
        return self.__host


if __name__ == '__main__':
    pass
