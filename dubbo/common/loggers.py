# -*- coding: utf-8 -*-
import logging

import sys
from datetime import datetime


class MyFormatter(logging.Formatter):
    """
    https://stackoverflow.com/questions/6290739/python-logging-use-milliseconds-in-time-format
    """

    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s.%03d" % (t, record.msecs)
        return s

    def format(self, record):
        level_name = record.levelname
        if level_name == 'ERROR':
            color = 31
        elif level_name == 'WARNING':
            color = 33
        elif level_name == 'INFO':
            color = 32
        else:
            color = 34
        while len(level_name) < 7:
            level_name += ' '
        record.levelname = '\033[{0}m{1}\033[0m'.format(color, level_name)
        return logging.Formatter.format(self, record)


def init_log():
    """
    初始化dubbo的日志配置
    :return:
    """
    logger = logging.getLogger('python-dubbo')
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = MyFormatter(
        '%(asctime)s %(levelname)s \033[35m%(process)-5d\033[0m --- [%(threadName)15s] \033[33m%(lineno)-4d\033[0m \033[36m%(filename)s\033[0m: %(message)s')
    console_handler.formatter = formatter
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)
