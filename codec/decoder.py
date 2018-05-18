# -*- coding: utf-8 -*-
from datetime import datetime

from common.constants import response_status_message
from common.util import *


class Response(object):
    """
    A class for parsing dubbo response body.
    All types can be parsed:
    * byte
    * boolean
    * int
    * double
    * string
    * object
    * list
    * map
    * null

    * type
    """

    def __init__(self, data):
        self.__data = data  # data是字节数组
        self.__index = 0  # 当前索引的位置

        self.types = []  # 保存所有通过read_type解析出来的type
        self.ref = []  # 保存所有引用类型的所有字段名称

    def get_byte(self):
        """
        获取到头部的字节数据，只是获取并不移动指针
        :return:
        """
        return self.__data[self.__index]

    def length(self):
        """
        当前的字节长度
        :return:
        """
        return len(self.__data) - self.__index

    def read_byte(self):
        """
        读取一个字节并向后移动一位指针
        :return:
        """
        value = self.__data[self.__index]
        self.__index += 1
        return value

    def read_bytes(self, num):
        """
        读取n个字节并向后移动n位指针
        :param num:
        :return:
        """
        value = self.__data[self.__index:self.__index + num]
        self.__index += num
        return value

    def read_boolean(self):
        """
        读取一个布尔类型
        :return:
        """
        value = self.read_byte()
        if value == ord('T'):
            return True
        elif value == ord('F'):
            return False
        else:
            raise Exception('illegal boolean value: {0}'.format(value))

    def read_int(self):
        """
        读取一个整型数据
        :return:
        """
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
        """
        读取一个浮点类型
        :return:
        """
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
            result = float(byte_list_2_num(self.read_bytes(4)) / 1000)
        elif value == ord('D'):
            result = struct.unpack('>d', self.read_bytes(8))[0]
        else:
            raise ValueError('{0} is not a float'.format(value))
        return result

    def _read_utf(self, length):
        """
        读取n个字符
        :param length:
        :return:
        """
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
        """
        读取一个字符串
        :return:
        """
        value = self.read_byte()
        buf = []
        while value == 0x52:
            length = byte_list_2_num(self.read_bytes(2))
            buf.extend(self._read_utf(length))
            value = self.read_byte()

        if value == ord('S'):
            length = byte_list_2_num(self.read_bytes(2))
        elif 0x00 <= value <= 0x1f:
            length = value
        else:
            length = (value - 0x30) << 8 | self.read_byte()

        buf.extend(self._read_utf(length))
        return str(bytearray(buf))

    def read_object(self):
        """
        读取一个对象
        :return:
        """
        result = {}

        value = self.read_byte()
        if 0x60 <= value <= 0x6f:
            ref = value - 0x60
            field_names = self.ref[ref]
            for field_name in field_names:
                field_value = self.read_string()
                result[field_name] = field_value
        elif value == ord('O'):
            ref = self.read_int()
            field_names = self.ref[ref]
            for field_name in field_names:
                field_value = self.read_string()
                result[field_name] = field_value
        elif value == ord('C'):
            path = self.read_string()

            field_length = self.read_int()
            field_names = []
            for i in range(field_length):
                field_names.append(self.read_string())

            # 由于Java中的类型名称在Python中不再有意义，所以此处我们只需要引用类型的字段名称
            self.ref.append(field_names)

            what_the_fuck = self.read_byte()

            for field_name in field_names:
                result[field_name] = self.read_next()

        return result

    def read_type(self):
        """
        读取一个type
        :return:
        """
        _type = self.read_next()
        if isinstance(_type, int):
            return self.types[_type]
        elif isinstance(_type, str):
            self.types.append(_type)
            return _type
        else:
            raise Exception('Unknown _type type for value: {0}'.format(_type))

    def read_list(self):
        """
        读取一个列表
        :return:
        """
        result = []

        value = self.read_byte()
        if 0x70 <= value <= 0x77:
            _type = self.read_type()  # type对于Python来说没有用处
            length = value - 0x70
            for i in range(length):
                result.append(self.read_next())
        elif 0x78 <= value <= 0x7f:
            length = value - 0x78
            for i in range(length):
                result.append(self.read_next())
        elif value == 0x55:
            _type = self.read_type()
            # 数组的内容为空
        elif value == 0x56:
            _type = self.read_type()
            length = self.read_int()
            for i in range(length):
                result.append(self.read_next())
        elif value == 0x57:
            pass
            # 数组的内容为空
        elif value == 0x58:
            length = self.read_int()
            for i in range(length):
                result.append(self.read_next())

        return result

    def read_long(self):
        """
        读取一个long类型的数字
        :return:
        """
        value = self.read_byte()
        if 0xd8 <= value <= 0xef:
            result = value - 0xe0
        elif 0xf0 <= value <= 0xff:
            result = ((value - 0xf8) << 8) | self.read_byte()
        elif 0x38 <= value <= 0x3f:
            i = (value - 0x3c) << 16
            i |= self.read_byte() << 8
            i |= self.read_byte()
            result = i
        elif value == 0x59:
            result = struct.unpack('>i', self.read_bytes(4))[0]
        elif value == ord('L'):
            result = struct.unpack('>q', self.read_bytes(8))[0]
        else:
            raise ValueError('{0} is not long type'.format(value))
        return result

    def read_null(self):
        """
        读取一个None
        :return:
        """
        value = self.read_byte()
        if value == ord('N'):
            return None
        else:
            raise Exception('{0} is not null'.format(value))

    def read_map(self):
        """
        读取一个dict
        :return:
        """
        value = self.read_byte()

        if value == ord('M') or value == ord('H'):
            result = {}
            while self.get_byte() != ord('Z'):
                key = self.read_next()
                value = self.read_next()
                result[key] = value
            self.read_byte()  # 干掉最后一个'Z'字符
            return result
        else:
            raise Exception('{0} is not a map.'.format(value))

    def read_date(self):
        """
        读取一个date类型的值
        :return:
        """
        value = self.read_byte()
        if value == 0x4a:
            timestamp = byte_list_2_num(self.read_bytes(8))
        elif value == 0x4b:
            timestamp = byte_list_2_num(self.read_bytes(4))
            timestamp *= 60000
        else:
            raise ValueError('{0} is not date type'.format(value))
        return datetime.fromtimestamp(timestamp / 1e3).strftime("%Y-%m-%dT%H:%M:%S+0800")

    def read_next(self):
        """
        读取下一个变量，自动识别变量类型
        :return:
        """
        data_type = self.get_byte()
        if data_type == ord('T') or data_type == ord('F'):
            return self.read_boolean()
        elif 0x80 <= data_type <= 0xd7 or data_type == ord('I'):
            return self.read_int()
        elif 0x5b <= data_type <= 0x5f or data_type == ord('D'):
            return self.read_double()
        elif 0xd8 <= data_type <= 0xff or 0x38 <= data_type <= 0x3f \
                or data_type == 0x59 or data_type == ord('L'):
            return self.read_long()
        elif 0x00 <= data_type <= 0x1f or 0x30 <= data_type <= 0x33 or data_type == 0x52 or data_type == ord('S'):
            return self.read_string()
        elif 0x60 <= data_type <= 0x6f or data_type == ord('O') or data_type == ord('C'):
            return self.read_object()
        elif 0x70 <= data_type <= 0x7f or 0x55 <= data_type <= 0x58:
            return self.read_list()
        elif data_type in (ord('H'), ord('M')):
            return self.read_map()
        elif data_type in (0x4a, 0x4b):
            return self.read_date()
        elif data_type == ord('N'):
            return self.read_null()
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
