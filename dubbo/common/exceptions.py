# -*- coding: utf-8 -*-


class DubboException(RuntimeError):
    pass


class DubboResponseException(DubboException):
    """
    dubbo服务端向客户端发送响应时所产生的异常
    """
    pass


class HessianTypeError(DubboException):
    """
    Hessian解码的时候发生了解析类型错误
    """
    pass


class RegisterException(DubboException):
    """
    与注册中心相关的异常
    """
    pass


class DubboRequestTimeoutException(DubboException):
    """
    dubbo请求超时异常
    """
    pass
