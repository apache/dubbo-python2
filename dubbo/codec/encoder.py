# -*- coding: utf-8 -*-
"""
把Python的数据结构根据Hessian协议序列化为相应的字节数组
当前支持的数据类型：
* bool
* int
* long
* float
* double
* java.lang.String
* java.lang.Object
"""
import struct

from dubbo.common.constants import MIN_INT_32, MAX_INT_32, DEFAULT_REQUEST_META
from dubbo.common.exceptions import HessianTypeError
from dubbo.common.util import double_to_long_bits, get_invoke_id


class Object(object):
    """
    创建一个Java对象
    """

    def __init__(self, path, values=None):
        """
        :param path:   Java对象的路径，例如：java.lang.Object
        :param values: 可以在创建对象时就进行赋值
        """
        if not isinstance(path, (str, unicode)):
            raise ValueError('Object path {} should be string type.'.format(path))
        self.__path = path
        if not isinstance(values, dict):
            values = {}
        self.__values = values

    def __getitem__(self, key):
        return self.__values[key]

    def __setitem__(self, key, value):
        if not isinstance(key, (str, unicode)):
            raise ValueError('Object key {} should be string type.'.format(key))
        self.__values[key] = value

    def __delitem__(self, key):
        del self.__values[key]

    def __repr__(self):
        return '<java object {} at {} with {}>'.format(self.__path, hex(id(self)), self.__values)

    def __contains__(self, key):
        return key in self.__values

    def keys(self):
        return self.__values.keys()

    def get_path(self):
        return self.__path


class Request(object):
    """
    A class for dumping dubbo request body.
    All types can be dumped:
    * boolean
    * int
    * long
    * double
    * string
    * object
    """

    def __init__(self, request):
        self.__body = request
        self.__classes = []
        self.types = []  # 泛型
        self.invoke_id = get_invoke_id()

    def encode(self):
        """
        把请求序列化为字节数组
        :return:
        """
        request_body = self._encode_request_body()
        invoke_id = list(bytearray(struct.pack('!q', self.invoke_id)))
        request_head = DEFAULT_REQUEST_META + invoke_id + get_request_body_length(request_body)
        return bytearray(request_head + request_body)

    def _get_parameter_types(self, arguments):
        """
        针对所有的参数计算得到参数类型字符串
        :param arguments:
        :return:
        """
        parameter_types = ''
        # 判断并得出参数的类型
        for argument in arguments:
            parameter_types += self._get_class_name(argument)
        return parameter_types

    def _get_class_name(self, _class):
        """
        根据一个字段的类型得到其在Java中对应类的全限定名
        转换规则：https://stackoverflow.com/a/3442100/4614538
        :param _class:
        :return:
        """
        if isinstance(_class, bool):  # bool类型的判断必须放在int类型判断的前面
            return 'Z'
        elif isinstance(_class, int):
            if MIN_INT_32 <= _class <= MAX_INT_32:
                return 'I'
            else:
                return 'J'
        elif isinstance(_class, float):
            return 'D'
        elif isinstance(_class, (str, unicode)):
            return 'L' + 'java/lang/String' + ';'
        elif isinstance(_class, Object):
            path = _class.get_path()
            path = 'L' + path.replace('.', '/') + ';'
            return path
        elif isinstance(_class, list):
            if len(_class) == 0:
                raise HessianTypeError('Method parameter {} is a list but length is zero'.format(_class))
            return '[' + self._get_class_name(_class[0])
        else:
            raise HessianTypeError('Unknown argument type: {0}'.format(_class))

    def _encode_request_body(self):
        """
        对所有的已知的参数根据dubbo协议进行编码
        :return:
        """
        dubbo_version = self.__body['dubbo_version']
        path = self.__body['path']
        version = self.__body['version']
        method = self.__body['method']
        arguments = self.__body['arguments']

        body = []
        body.extend(self._encode_single_value(dubbo_version))
        body.extend(self._encode_single_value(path))
        body.extend(self._encode_single_value(version))
        body.extend(self._encode_single_value(method))
        body.extend(self._encode_single_value(self._get_parameter_types(arguments)))
        for argument in arguments:
            body.extend(self._encode_single_value(argument))

        attachments = {
            'path': path,
            'interface': path,
            'version': version
        }
        # attachments参数以H开头，以Z结尾
        body.append(ord('H'))
        for key in attachments.keys():
            value = attachments[key]
            body.extend(self._encode_single_value(key))
            body.extend(self._encode_single_value(value))
        body.append(ord('Z'))

        # 因为在上面的逻辑中没有对byte大小进行检测，所以在这里进行统一的处理
        for i in xrange(len(body)):
            body[i] = body[i] & 0xff
        return body

    @staticmethod
    def _encode_bool(value):
        """
        对bool类型进行编码
        :param value:
        :return:
        """
        result = []
        if value:
            result.append(ord('T'))
        else:
            result.append(ord('F'))
        return result

    @staticmethod
    def _encode_int(value):
        """
        对整数进行编码
        :param value:
        :return:
        """
        result = []
        # 超出int类型范围的值则转化为long类型
        # 这里问题在于对于落在int范围内的数字，我们无法判断其是long类型还是int类型，所以一律认为其是int类型
        if value > MAX_INT_32 or value < MIN_INT_32:
            result.append(ord('L'))
            result.extend(list(bytearray(struct.pack('!q', value))))
            return result

        if -0x10 <= value <= 0x2f:
            result.append(value + 0x90)
        elif -0x800 <= value <= 0x7ff:
            result.append(0xc8 + (value >> 8))
            result.append(value)
        elif -0x40000 <= value <= 0x3ffff:
            result.append(0xd4 + (value >> 16))
            result.append(value >> 8)
            result.append(value)
        else:
            result.append(ord('I'))
            result.append(value >> 24)
            result.append(value >> 16)
            result.append(value >> 8)
            result.append(value)
        return result

    @staticmethod
    def _encode_float(value):
        """
        对浮点类型进行编码
        :param value:
        :return:
        """
        result = []
        int_value = int(value)
        if int_value == value:
            if int_value == 0:
                result.append(0x5b)
                return result
            elif int_value == 1:
                result.append(0x5c)
                return result
            elif -0x80 <= int_value < 0x80:
                result.append(0x5d)
                result.append(int_value)
                return result
            elif -0x8000 <= int_value < 0x8000:
                result.append(0x5e)
                result.append(int_value >> 8)
                result.append(int_value)
                return result

        mills = int(value * 1000)
        if 0.001 * mills == value and MIN_INT_32 <= mills <= MAX_INT_32:
            result.append(0x5f)
            result.append(mills >> 24)
            result.append(mills >> 16)
            result.append(mills >> 8)
            result.append(mills)
            return result

        bits = double_to_long_bits(value)
        result.append(ord('D'))
        result.append(bits >> 56)
        result.append(bits >> 48)
        result.append(bits >> 40)
        result.append(bits >> 32)
        result.append(bits >> 24)
        result.append(bits >> 16)
        result.append(bits >> 8)
        result.append(bits)
        return result

    @staticmethod
    def _encode_utf(value):
        """
        对字符串进行编码，编码格式utf-8
        参见方法：com.alibaba.com.caucho.hessian.io.Hessian2Output#printString
        :param value:
        :return:
        """
        result = []
        for v in value:
            ch = ord(v)
            if ch < 0x80:
                result.append(ch & 0xff)
            elif ch < 0x800:
                result.append((0xc0 + ((ch >> 6) & 0x1f)) & 0xff)
                result.append((0x80 + (ch & 0x3f)) & 0xff)
            else:
                result.append((0xe0 + ((ch >> 12) & 0xf)) & 0xff)
                result.append((0x80 + ((ch >> 6) & 0x3f)) & 0xff)
                result.append((0x80 + (ch & 0x3f)) & 0xff)
        return result

    def _encode_str(self, value):
        """
        对一个字符串进行编码
        :param value:
        :return:
        """
        result = []
        # 在进行网络传输操作时一律使用unicode进行操作
        if isinstance(value, str):
            value = value.decode('utf-8')
        length = len(value)
        if length <= 0x1f:
            result.append(0x00 + length)
        elif length <= 0x3ff:
            result.append(0x30 + (length >> 8))
            result.append(length)
        else:
            result.append(ord('S'))
            result.append(length >> 8)
            result.append(length)

        result.extend(self._encode_utf(value))
        return result

    def _encode_object(self, value):
        """
        对一个对象进行编码
        :param value:
        :return:
        """
        result = []
        path = value.get_path()
        field_names = value.keys()

        if path not in self.__classes:
            result.append(ord('C'))
            result.extend(self._encode_single_value(path))

            result.extend(self._encode_single_value(len(field_names)))

            for field_name in field_names:
                result.extend(self._encode_single_value(field_name))
            self.__classes.append(path)
        class_id = self.__classes.index(path)
        if class_id <= 0xf:
            class_id += 0x60
            class_id &= 0xff
            result.append(class_id)
        else:
            result.append(ord('O'))
            result.extend(self._encode_single_value(class_id))
        for field_name in field_names:
            result.extend(self._encode_single_value(value[field_name]))
        return result

    def _encode_list(self, value):
        """
        对一个列表进行编码
        :param value:
        :return:
        """
        result = []
        length = len(value)
        if length == 0:
            # 没有值则无法判断类型，一律返回null
            return self._encode_single_value(None)
        if isinstance(value[0], bool):
            _type = '[boolean'
        elif isinstance(value[0], int):
            _type = '[int'
        elif isinstance(value[0], float):
            _type = '[double'
        elif isinstance(value[0], str):
            _type = '[string'
        elif isinstance(value[0], Object):
            _type = '[object'
        else:
            raise HessianTypeError('Unknown list type: {}'.format(value[0]))
        if length < 0x7:
            result.append(0x70 + length)
            if _type not in self.types:
                self.types.append(_type)
                result.extend(self._encode_single_value(_type))
            else:
                result.extend(self._encode_single_value(self.types.index(_type)))
        else:
            result.append(0x56)
            if _type not in self.types:
                self.types.append(_type)
                result.extend(self._encode_single_value(_type))
            else:
                result.extend(self._encode_single_value(self.types.index(_type)))
            result.extend(self._encode_single_value(length))
        for v in value:
            if type(value[0]) != type(v):
                raise HessianTypeError('All elements in list must be the same type, first type'
                                       ' is {0} but current type is {1}'.format(type(value[0]), type(v)))
            result.extend(self._encode_single_value(v))
        return result

    def _encode_single_value(self, value):
        """
        根据hessian协议对单个变量进行编码
        :param value:
        :return:
        """
        # 布尔类型
        if isinstance(value, bool):
            return self._encode_bool(value)
        # 整型（包括长整型）
        elif isinstance(value, int):
            return self._encode_int(value)
        # 浮点类型
        elif isinstance(value, float):
            return self._encode_float(value)
        # 字符串类型
        elif isinstance(value, (str, unicode)):
            return self._encode_str(value)
        # 对象类型
        elif isinstance(value, Object):
            return self._encode_object(value)
        # 列表(list)类型，不可以使用tuple替代
        elif isinstance(value, list):
            return self._encode_list(value)
        # null
        elif value is None:
            return [ord('N')]
        else:
            raise HessianTypeError('Unknown argument type: {}'.format(value))


def get_request_body_length(body):
    """
    获取body的长度，并将其转为长度为4个字节的字节数组
    :param body:
    :return:
    """
    return list(bytearray(struct.pack('!i', len(body))))


if __name__ == '__main__':
    pass
