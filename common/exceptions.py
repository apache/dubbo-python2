# -*- coding: utf-8 -*-


class DubboException(Exception):
    pass


class HessianTypeError(Exception):
    """
    Hessian解码的时候发生了解析类型错误
    """
    pass


class RegisterException(Exception):
    """
    与注册中心相关的异常
    """
    pass
