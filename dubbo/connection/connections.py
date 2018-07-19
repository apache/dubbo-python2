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
    TIMEOUT_CHECK_INTERVAL, TIMEOUT_IDLE, TIMEOUT_MAX_TIMES, DEFAULT_READ_PARAMS
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
        self.conn_lock = threading.Lock()
        # 用于在数据读取完毕之后唤醒主线程
        self.conn_events = {}

        reading_thread = threading.Thread(target=self._read_from_server)
        reading_thread.setDaemon(True)  # 当主线程退出时此线程同时退出
        reading_thread.start()

        scanning_thread = threading.Thread(target=self._send_heartbeat)
        scanning_thread.setDaemon(True)
        scanning_thread.start()

    def get(self, host, request_param, timeout=None):
        """
        执行远程调用获取数据
        :param host:
        :param request_param:
        :param timeout:
        :return:
        """
        conn = self._get_connection(host)
        request = Request(request_param)
        request_data = request.encode()
        invoke_id = request.invoke_id

        event = threading.Event()
        self.conn_events[invoke_id] = event
        # 发送数据
        conn.send(request_data)
        event.wait(timeout)
        del self.conn_events[invoke_id]

        if invoke_id not in self.results:
            err = "Socket(host='{}'): Read timed out. (read timeout={})".format(host, timeout)
            raise DubboRequestTimeoutException(err)

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
            self.conn_lock.acquire()
            try:
                if host not in self._connection_pool:
                    self.client_heartbeats[host] = 0
                    self._new_connection(host)
            finally:
                self.conn_lock.release()
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

    def _callback(self, data, conn, data_type, invoke_id):
        """
        读取的数据满足之后触发的回调函数，由于connection是共有
        的，所以我们要把这一大坨和连接相关的状态保存在各自连接中
        :param data: 收到的数据
        :param conn: 对应的连接
        :param data_type:
                1 头部
                2 因为头部的解析错误，需要被读取的错误body
                3 正确的body
        :param invoke_id
        :return:
            next_read_length 下一次读取需要读取的数据长度
            next_read_type   下一次读取需要读取的数据类型
            invoke_id        此次调用的id
        """
        # 关闭连接
        if not data:
            host = conn.remote_host()
            logger.debug('{} closed by remote server'.format(host))
            self._delete_connection(conn)
            return 0, 0, 0

        if data_type == 1:
            return self._parse_head(data, conn)
        elif data_type == 2:
            res = Response(data)
            error = res.read_next()

            self.results[invoke_id] = DubboResponseException('\n{}'.format(error))
            self.conn_events[invoke_id].set()
            # 下一次继续读取新的头部数据
            return DEFAULT_READ_PARAMS
        elif data_type == 3:
            self._parse_response(invoke_id, data)
            # 下一次继续读取新的头部数据
            return DEFAULT_READ_PARAMS
        else:
            raise RuntimeError('Unknown data type {}.'.format(data_type))

    def _parse_head(self, data, conn):
        """
        对dubbo响应的头部信息进行解析
        :param data:
        :param conn:
        :return:
        """
        try:
            heartbeat, body_length = parse_response_head(data)
        except DubboResponseException as e:  # 这里是dubbo的内部异常，与response中的业务异常不一样
            logger.exception(e)
            body_length = unpack('!i', data[12:])[0]
            # 获取响应的invoke_id
            invoke_id = unpack('!q', data[4:12])[0]
            # 下一次需要读取错误的响应体
            return body_length, 2, invoke_id
        # 远程主机发送的心跳请求数据包
        if heartbeat == 2:
            logger.debug('❤ request  -> {}'.format(conn.remote_host()))
            msg_id = data[4:12]
            heartbeat_response = CLI_HEARTBEAT_RES_HEAD + list(msg_id) + CLI_HEARTBEAT_TAIL
            conn.write(bytearray(heartbeat_response))
            # 下一次继续读取新的头部数据
            return DEFAULT_READ_PARAMS
        # 远程主机发送的心跳响应数据包
        elif heartbeat == 1:
            logger.debug('❤ response -> {}'.format(conn.remote_host()))
            host = conn.remote_host()
            self.client_heartbeats[host] -= 1
            # 下一次继续读取新的头部数据
            return DEFAULT_READ_PARAMS
        # 普通的数据包
        else:
            # 获取响应的invoke_id
            invoke_id = unpack('!q', data[4:12])[0]
            # 下一次读取正常的响应体
            return body_length, 3, invoke_id

    def _parse_response(self, invoke_id, body):
        """
        对dubbo的响应数据进行解析
        :param invoke_id:
        :param body:
        :return:
        """
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
            self.conn_events[invoke_id].set()  # 唤醒请求线程

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
                self._check_conn(host)
            ending = time.time()
            time_delta = ending - starting
            if time_delta < TIMEOUT_CHECK_INTERVAL:
                time.sleep(TIMEOUT_CHECK_INTERVAL - time_delta)

    def _check_conn(self, host):
        """
        对连接进行检查，查看是否超时或者已经达到最大的超时次数
        :param host:
        :return:
        """
        conn = self._connection_pool[host]
        # 如果未达到最大的超时时间，则不进行任何操作
        if time.time() - conn.last_active <= TIMEOUT_IDLE:
            return

        # 达到最大的超时次数，移除此连接
        if self.client_heartbeats[host] >= TIMEOUT_MAX_TIMES:
            self._delete_connection(conn)
            conn.close()  # 客户端主动关闭连接
            logger.debug('{} closed by client'.format(host))

        # 未达到最大的超时次数，超时次数+1且发送心跳包
        else:
            self.client_heartbeats[host] += 1
            invoke_id = list(bytearray(pack('!q', get_invoke_id())))
            req = CLI_HEARTBEAT_REQ_HEAD + invoke_id + CLI_HEARTBEAT_TAIL
            conn.write(bytearray(req))


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
                readable, writeable, exceptional = select.select(conns, conns, [], self.select_timeout)
            except select.error as e:
                logger.exception(e)
                break
            for conn in writeable:
                conn.write()
            for conn in readable:
                conn.read(self._callback)

    def _new_connection(self, host):
        ip, port = host.split(':')
        self._connection_pool[host] = Connection(ip, int(port))
        # 保证select模型已经开始监听最新加入的这个fd的读事件，否则可能会导致此fd读事件丢失
        time.sleep(self.select_timeout)

    def _delete_connection(self, conn):
        del self._connection_pool[conn.remote_host()]


# connection_pool在整个进程中是单例的
connection_pool = SelectConnectionPool()


class Connection(object):
    """
    对Socket链接做了一些封装
    """

    def __init__(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        # 在创建好连接之后设置IO为非阻塞
        sock.setblocking(False)
        self.__sock = sock
        self.__host = '{0}:{1}'.format(host, port)

        self.read_length, self.read_type, self.invoke_id = DEFAULT_READ_PARAMS
        self.read_buffer = []
        self.write_buffer = []
        self.write_lock = threading.Lock()

        self.last_active = time.time()

    def fileno(self):
        """
        Get file descriptor
        https://stackoverflow.com/a/39328021/4614538
        :return:
        """
        return self.__sock.fileno()

    def send(self, data):
        """
        客户端执行发送操作
        :param data:
        :return:
        """
        self.write_lock.acquire()
        try:
            self.write_buffer.extend(list(data))
        finally:
            self.write_lock.release()

    def write(self):
        """
        向远程主机写数据
        :return:
        """
        if len(self.write_buffer) == 0:
            return
        self.write_lock.acquire()
        try:
            if len(self.write_buffer) > 0:
                length = self.__sock.send(bytearray(self.write_buffer))
                self.write_buffer = self.write_buffer[length:]
                self.last_active = time.time()
        finally:
            self.write_lock.release()

    def read(self, callback):
        """
        读取远程主机的数据
        :param callback:
        :return:
        """
        self.last_active = time.time()

        data = list(bytearray(self.__sock.recv(self.read_length - len(self.read_buffer))))
        # 断开连接
        if not data:
            callback([], self, None, None)
            return

        self.read_buffer.extend(data)
        # 数据读取已经满足要求
        if len(self.read_buffer) == self.read_length:
            self.read_length, self.read_type, self.invoke_id \
                = callback(bytearray(self.read_buffer), self, self.read_type, self.invoke_id)
            self.read_buffer = []

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
