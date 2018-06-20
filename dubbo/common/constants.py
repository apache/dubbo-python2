# -*- coding: utf-8 -*-

from util import num_2_byte_list

# 服务端的响应码
response_status_message = {
    20: 'OK',
    30: 'CLIENT_TIMEOUT',
    31: 'SERVER_TIMEOUT',
    40: 'BAD_REQUEST',
    50: 'BAD_RESPONSE',
    60: 'SERVICE_NOT_FOUND',
    70: 'SERVICE_ERROR',
    80: 'SERVER_ERROR',
    90: 'CLIENT_ERROR'
}

INT_DIRECT_MIN = -0x10
INT_DIRECT_MAX = 0x2f
BC_INT_ZERO = 0x90

INT_BYTE_MIN = -0x800
INT_BYTE_MAX = 0x7ff
BC_INT_BYTE_ZERO = 0xc8

INT_SHORT_MIN = -0x40000
INT_SHORT_MAX = 0x3ffff
BC_INT_SHORT_ZERO = 0xd4

BC_LONG_INT = 0x59
BC_LONG_ZERO = 0xe0
BC_LONG_BYTE_ZERO = 0xf8
BC_LONG_SHORT_ZERO = 0x3c

BC_DOUBLE_ZERO = 0x5b
BC_DOUBLE_ONE = 0x5c
BC_DOUBLE_BYTE = 0x5d
BC_DOUBLE_SHORT = 0x5e
BC_DOUBLE_MILL = 0x5f

BC_STRING_DIRECT = 0x00
STRING_DIRECT_MAX = 0x1f
BC_STRING_SHORT = 0x30
STRING_SHORT_MAX = 0x3ff

# 32位整型的最大值
MAX_INT_32 = 2147483647
# 32位整型的最小值
MIN_INT_32 = -2147483648

# MAGIC_NUM(2) + FLAG(1) + STATUS(1) + INVOKE_ID(8)
DEFAULT_REQUEST_META = num_2_byte_list(0xdabbc2000000000000000000)

# 客户端对服务端发送的心跳的请求的头部
CLI_HEARTBEAT_REQ_HEAD = num_2_byte_list(0xdabbe2) + [0]
# 客户端对服务端发送的心跳的响应的头部
CLI_HEARTBEAT_RES_HEAD = num_2_byte_list(0xdabb2214)
# 心跳尾部
CLI_HEARTBEAT_TAIL = [0, 0, 0, 1] + num_2_byte_list(0x4e)

DUBBO_ZK_PROVIDERS = '/dubbo/{}/providers'
DUBBO_ZK_CONSUMERS = '/dubbo/{}/consumers'
DUBBO_ZK_CONFIGURATORS = '/dubbo/{}/configurators'
