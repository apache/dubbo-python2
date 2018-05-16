# -*- coding: utf-8 -*-
import socket


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
