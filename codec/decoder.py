# -*- coding: utf-8 -*-
from common.constants import response_status_message
from common.util import *


class Response(object):
    def __init__(self, data):
        self.__data = data
        self.types = []  # 保存所有通过read_type解析出来的type
        self.ref = []  # 引用类型
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

    def _read_utf(self, length):
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
        result = {}

        value = self.read_byte()
        if 0x60 <= value <= 0x6f:
            ref = value - 0x60
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
        value = self.read_byte()
        if value == 0x52 or value == ord('S') or (0x00 <= value <= 0x1f) or (0x30 <= value <= 0x33):
            _type = self.read_string()
            self.types.append(_type)
            return _type
        else:
            ref = self.read_int()
            return self.types[ref]

    def read_list(self):
        result = []

        value = self.read_byte()
        if 0x70 <= value <= 0x77:
            _type = self.read_type()
            length = value - 0x70
        elif 0x78 <= value <= 0x7f:
            length = value - 0x78
            for i in range(length):
                result.append(self.read_object())
        elif value == 0x55:
            _type = self.read_type()
        elif value == 0x56:
            _type = self.read_type()
            lenght = self.read_int()
        elif value == 0x57:
            pass
        elif value == 0x58:
            length = self.read_int()

        return result

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
        elif 0x00 <= data_type <= 0x1f or data_type == ord('S'):
            return self.read_string()
        elif 0x60 <= data_type <= 0x6f or data_type == ord('C'):
            return self.read_object()
        elif 0x70 <= data_type <= 0x7f or 0x55 <= data_type <= 0x58:
            return self.read_list()
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
