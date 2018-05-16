# -*- coding: utf-8 -*-
from StringIO import StringIO

from common.constants import response_status_message
from common.util import *


class Response(object):
    def __init__(self, data):
        self.__data = data

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
            result = float(byte_list_2_num(self.read_byte()))
        elif value == 0x5e:
            result = float(byte_list_2_num(self.read_bytes(2)))
        elif value == 0x5f:
            result = byte_list_2_num(self.read_bytes(4))
        else:
            result = byte_list_2_num(self.read_bytes(8))
        return result

    def __read_utf(self, output, length):
        while length > 0:
            c = self.read_byte()
            output.write(chr(c))
            if c < 0x80:
                pass
            elif (c & 0xe0) == 0xc0:
                output.write(self.read_bytes(1))
            elif (c & 0xf0) == 0xe0:
                output.write(self.read_bytes(2))
            elif (c & 0xf8) == 0xf0:
                output.write(self.read_bytes(3))
            length -= 1

    def read_string(self):
        value = self.read_byte()
        buf = StringIO()
        while value == 0x52:
            length = byte_list_2_num(self.read_bytes(2))
            self.__read_utf(buf, length)
            value = self.read_byte()

        if value == ord('S'):
            length = byte_list_2_num(self.read_bytes(2))
        elif 0x00 <= value <= 0x1f:
            length = value
        else:
            length = (value - 0x30) << 8 | self.read_byte()

        self.__read_utf(buf, length)
        result = buf.getvalue().decode('utf-8')
        return result

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
                print self.read_object()

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
    data = 0x9143186d652e686f757275692e6563686f2e6265616e2e5573657294036167650673616c61727909677261647561746564046e616d6560a25e07d04643186d652e686f757275692e6563686f2e6265616e2e4e616d65920966697273744e616d65086c6173744e616d656101e5bca001e4b889
    r = Response(num_2_byte_list(data))
    print r.read_int()

    while r.length() > 0:
        print r.read_object()
