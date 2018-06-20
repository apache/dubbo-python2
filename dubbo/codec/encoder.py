# -*- coding: utf-8 -*-
import struct

from dubbo.common.constants import DEFAULT_REQUEST_META, INT_DIRECT_MAX, INT_DIRECT_MIN, BC_INT_ZERO, INT_BYTE_MAX, \
    INT_BYTE_MIN, BC_INT_BYTE_ZERO, INT_SHORT_MIN, INT_SHORT_MAX, BC_INT_SHORT_ZERO, BC_DOUBLE_ZERO, BC_DOUBLE_ONE, \
    BC_DOUBLE_BYTE, BC_DOUBLE_MILL, STRING_DIRECT_MAX, BC_STRING_DIRECT, STRING_SHORT_MAX, BC_STRING_SHORT, \
    BC_DOUBLE_SHORT
from dubbo.common.exceptions import HessianTypeError
from dubbo.common.util import double_to_long_bits, num_2_byte_list


def encode(request):
    """
    把请求序列化为字节数组
    :param request:
    :return:
    """
    request_body = _encode_request_body(request)
    request_head = DEFAULT_REQUEST_META + _get_request_body_length(request_body)
    return bytearray(request_head + request_body)


def _encode_request_body(body):
    """
    对所有的已知的参数根据dubbo协议进行编码
    :param body:
    :return:
    """
    dubbo_version = body['dubbo_version']
    path = body['path']
    version = body['version']
    method = body['method']
    arguments = body['arguments']

    parameter_types = ''
    # 判断并得出参数的类型
    for argument in arguments:
        if isinstance(argument, bool):  # bool类型的判断必须放在int类型判断的前面
            parameter_types += 'Z'
        elif isinstance(argument, int):
            if -2147483648 <= argument <= 2147483647:
                parameter_types += 'I'
            else:
                parameter_types += 'J'
        elif isinstance(argument, float):
            parameter_types += 'D'
        elif isinstance(argument, str):
            parameter_types += 'Ljava/lang/String;'
        else:
            raise HessianTypeError('Unknown argument type: {0}'.format(argument))

    body = []
    body.extend(_encode_single_value(dubbo_version))
    body.extend(_encode_single_value(path))
    body.extend(_encode_single_value(version))
    body.extend(_encode_single_value(method))
    body.extend(_encode_single_value(parameter_types))
    for argument in arguments:
        body.extend(_encode_single_value(argument))

    attachments = {
        'path': path,
        'interface': path,
        'version': version
    }
    # attachments参数以H开头，以Z结尾
    body.append(ord('H'))
    for key in attachments.keys():
        value = attachments[key]
        body.extend(_encode_single_value(key))
        body.extend(_encode_single_value(value))
    body.append(ord('Z'))

    # 因为在上面的逻辑中没有对byte大小进行检测，所以在这里进行统一的处理
    for i in range(len(body)):
        body[i] = body[i] & 0xff
    return body


def _encode_single_value(value):
    """
    根据hessian协议对单个变量进行编码
    :param value:
    :return:
    """
    result = []
    if isinstance(value, bool):
        if value:
            result.append(ord('T'))
        else:
            result.append(ord('F'))
        return result
    elif isinstance(value, int):
        if value > 2147483647 or value < -2147483648:
            result.append(ord('L'))
            result.extend(list(bytearray(struct.pack('>q', value))))
            return result

        if INT_DIRECT_MIN <= value <= INT_DIRECT_MAX:
            result.append(value + BC_INT_ZERO)
        elif INT_BYTE_MIN <= value <= INT_BYTE_MAX:
            result.append(BC_INT_BYTE_ZERO + (value >> 8))
            result.append(value)
        elif INT_SHORT_MIN <= value <= INT_SHORT_MAX:
            result.append(BC_INT_SHORT_ZERO + (value >> 16))
            result.append(value >> 8)
            result.append(value)
        else:
            result.append(ord('I'))
            result.append(value >> 24)
            result.append(value >> 16)
            result.append(value >> 8)
            result.append(value)
        return result
    elif isinstance(value, float):
        int_value = int(value)
        if int_value == value:
            if int_value == 0:
                result.append(BC_DOUBLE_ZERO)
                return result
            elif int_value == 1:
                result.append(BC_DOUBLE_ONE)
                return result
            elif -0x80 <= int_value < 0x80:
                result.append(BC_DOUBLE_BYTE)
                result.append(int_value)
                return result
            elif -0x8000 <= int_value < 0x8000:
                result.append(BC_DOUBLE_SHORT)
                result.append(int_value >> 8)
                result.append(int_value)
                return result

        mills = int(value * 1000)
        if 0.001 * mills == value and -2147483648 <= mills <= 2147483647:
            result.append(BC_DOUBLE_MILL)
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
    elif isinstance(value, str):
        # 根据hessian协议这里的长度必须是字符串长度而不是字节长度，所以需要Unicode类型
        length = len(value.decode('utf-8'))
        if length <= STRING_DIRECT_MAX:
            result.append(BC_STRING_DIRECT + length)
        elif length <= STRING_SHORT_MAX:
            result.append(BC_STRING_SHORT + (length >> 8))
            result.append(length)
        else:
            result.append(ord('S'))
            result.append(length >> 8)
            result.append(length)
        result.extend(list(bytearray(value)))  # 加上变量数组
        return result
    else:
        raise HessianTypeError('Unknown argument type: {0}'.format(value))


def _get_request_body_length(body):
    """
    获取body的长度，并将其转为长度为4个字节的字节数组
    :param body:
    :return:
    """
    request_body_length = num_2_byte_list(len(body))
    # 用4个字节表示请求body的长度
    while len(request_body_length) < 4:
        request_body_length = [0] + request_body_length
    return request_body_length
