# -*- coding: utf-8 -*-
from common.constants import response_status_message
from common.util import *


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
