# -*- coding: utf-8 -*-
from common.constants import response_status_message
from common.util import *


class Response(object):
    def __init__(self, data):
        self.__data = data
        self.__result = {}  # 用于保存最终结果

    def get_byte(self):
        return self.__data[0]

    def length(self):
        return len(self.__data)

    def read_byte(self):
        value = self.__data[0]
        del self.__data[0]
        return value

    def read_bytes(self, num):
        value = self.__data[:num]
        del self.__data[:num]
        return value

    def read_boolean(self):
        value = self.read_byte()
        if value == ord('T'):
            return True
        elif value == ord('F'):
            return False
        else:
            raise Exception('illegal boolean value: {0}'.format(value))

    def read_int(self):
        value = self.read_byte()
        if 0x80 <= value <= 0xbf:
            result = value - 0x90
        elif 0xc0 <= value <= 0xcf:
            i = (value - 0xc8) << 8
            i |= self.read_byte()
            result = i
        elif 0xd0 <= value <= 0xd7:
            i = (value - 0xd4) << 16
            i |= self.read_byte() << 8
            i |= self.read_byte()
            result = i
        else:
            result = byte_list_2_num(self.read_bytes(4))
        return result

    def read_double(self):
        value = self.read_byte()
        if value == 0x5b:
            result = 0.0
        elif value == 0x5c:
            result = 1.0
        elif value == 0x5d:
            result = float(byte_list_2_num(self.read_bytes(1)))
        elif value == 0x5e:
            result = float(byte_list_2_num(self.read_bytes(2)))
        elif value == 0x5f:
            result = byte_list_2_num(self.read_bytes(4))
        else:
            result = byte_list_2_num(self.read_bytes(8))
        return result

    def __read_utf(self, length):
        value = []
        while length > 0:
            c = self.read_byte()
            value.append(c)
            if c < 0x80:
                pass
            elif (c & 0xe0) == 0xc0:
                value.extend(self.read_bytes(1))
            elif (c & 0xf0) == 0xe0:
                value.extend(self.read_bytes(2))
            elif (c & 0xf8) == 0xf0:
                value.extend(self.read_bytes(3))
            length -= 1
        return value

    def read_string(self):
        value = self.read_byte()
        buf = []
        while value == 0x52:
            length = byte_list_2_num(self.read_bytes(2))
            buf.extend(self.__read_utf(length))
            value = self.read_byte()

        if value == ord('S'):
            length = byte_list_2_num(self.read_bytes(2))
        elif 0x00 <= value <= 0x1f:
            length = value
        else:
            length = (value - 0x30) << 8 | self.read_byte()

        buf.extend(self.__read_utf(length))
        return str(bytearray(buf))

    def read_object(self):
        if not ord('C') == self.read_byte():
            raise Exception('This is not a object')

        path = self.read_string()
        print path

        field_length = self.read_int()
        field_names = []
        for i in range(field_length):
            field_names.append(self.read_string())
        print field_names

        what_the_fuck = self.read_byte()
        self.read_next()

    def read_list(self):
        length = self.read_byte()
        self.read_next()

    def read_next(self):
        """
        读取下一个变量，自动识别变量类型
        :return:
        """
        while self.length() > 0:
            data_type = self.get_byte()
            if data_type == ord('T') or data_type == ord('F'):
                print self.read_boolean()
            elif 0x80 <= data_type <= 0xd7 or data_type == ord('I'):
                print self.read_int()
            elif 0x5b <= data_type <= 0x5f or data_type == ord('D'):
                print self.read_double()
            elif 0x00 <= data_type <= 0x1f or data_type == ord('S'):
                print self.read_string()
            elif data_type == ord('C'):
                self.read_object()
            elif 0x78 <= data_type <= 0x7f:
                self.read_list()
            elif data_type == ord('a'):
                what_the_fuck = self.read_byte()
            else:
                raise Exception('Unknown param type.')

    def __repr__(self):
        return str(self.__data)


def get_response_body_length(response_head):
    """
    计算出响应体的长度
    :param response_head:
    :return:
    """
    # Magic number
    if not (response_head[0] == 0xda and response_head[1] == 0xbb):
        raise Exception('illegal response')
    response_status = response_head[3]
    if response_status != 20:
        raise Exception(response_status_message[response_status])
    return byte_list_2_num(response_head[12:])


if __name__ == '__main__':
    pass
