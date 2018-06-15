# -*- coding: utf-8 -*-
from random import randint
from urllib import quote
from urlparse import urlparse, unquote, parse_qsl

import time

import logging
from kazoo.client import KazooClient

from common.exceptions import RegisterException
from common.util import get_ip, get_pid
from connection.connections import DUBBO_ZK_PROVIDERS, DUBBO_ZK_CONSUMERS, DUBBO_ZK_CONFIGURATORS

logger = logging.getLogger('dubbo.py')


class ZkRegister(object):
    """
    ZkRegister的主要作用：
    1. 根据特定的interface从zk中取出与之相关的所有provider的host并且监听
       provider的变化，当发生变化时更新最新的hosts到本地缓存；
    2. 当从zk中获取指定的interface的provider的时候，把当前进程作为此interface
       的一个consumer注册到zk中，并设置此节点的状态为ephemeral；
    """

    def __init__(self, hosts, application_name='search_platform'):
        """
        :param hosts: Zookeeper的地址
        :param application_name: 当前客户端的名称
        """
        zk = KazooClient(hosts=hosts)
        zk.start()

        self.zk = zk
        self.hosts = {}
        self.weights = {}
        self.application_name = application_name

    def get_provider_host(self, interface):
        """
        从zk中可以根据接口名称获取到此接口某个provider的host
        :param interface:
        :return:
        """
        if not self.hosts.get(interface):
            path = DUBBO_ZK_PROVIDERS.format(interface)
            if self.zk.exists(path):
                providers = self.zk.get_children(path, watch=self._watch_children)
                if len(providers) == 0:
                    raise RegisterException('no providers for interface {}'.format(interface))
                providers = map(parse_url, providers)
                self._register_consumer(providers)
                self.hosts[interface] = map(lambda provider: provider['host'], providers)

                # 试图从配置中取出权重相关的信息
                configurators = self.zk.get_children(DUBBO_ZK_CONFIGURATORS.format(interface),
                                                     watch=self._watch_configurators)
                if configurators:
                    configurators = map(parse_url, configurators)
                    conf = {}
                    for configurator in configurators:
                        conf[configurator['host']] = configurator['fields'].get('weight', 100)  # 默认100
                    self.weights[interface] = conf
            else:
                raise RegisterException('can\'t providers for interface {0}'.format(interface))
        return self._routing_with_wight(interface)

    def _routing_with_wight(self, interface):
        """
        根据接口名称以及配置好的权重信息获取一个host
        :param interface:
        :return:
        """
        hosts = self.hosts[interface]
        # 此接口没有权重设置，使用朴素的路由算法
        if not self.weights.get(interface):
            return hosts[randint(0, len(hosts) - 1)]

        weights = self.weights[interface]
        hosts_weight = []
        for host in hosts:
            hosts_weight.append(int(weights.get(host, '100')))

        hit = randint(0, sum(hosts_weight) - 1)
        for i in range(len(hosts)):
            if hit <= sum(hosts_weight[:i + 1]):
                return hosts[i]

        raise RegisterException('error for finding [{}] host with weight.'.format(interface))

    def _watch_children(self, event):
        """
        对某个provider下的子节点进行监听，一旦provider发生了变化则对本地缓存进行更新
        :param event:
        :return:
        """
        path = event.path
        interface = path.split('/')[2]

        providers = self.zk.get_children(path, watch=self._watch_children)
        logger.debug('{} providers: {}'.format(interface, providers))
        if len(providers) == 0:
            logger.debug('no providers for interface {}'.format(interface))
            del self.hosts[interface]
            return
        providers = map(parse_url, providers)
        self.hosts[interface] = map(lambda provider: provider['host'], providers)

    def _watch_configurators(self, event):
        """
        监测某个interface中provider的权重的变化信息
        :param event:
        :return:
        """
        path = event.path
        interface = path.split('/')[2]

        # 试图从配置中取出权重相关的信息
        configurators = self.zk.get_children(DUBBO_ZK_CONFIGURATORS.format(interface),
                                             watch=self._watch_configurators)
        if configurators:
            configurators = map(parse_url, configurators)
            conf = {}
            for configurator in configurators:
                conf[configurator['host']] = configurator['fields'].get('weight', 100)
            self.weights[interface] = conf
        else:
            # 没有权重配置则意味着此配置可以被删除
            del self.weights[interface]

    def _register_consumer(self, providers):
        """
        把本机注册到对应的interface的consumer上去
        :param providers:
        :return:
        """
        provider = providers[0]
        provider_fields = provider['fields']

        consumer = 'consumer://' + get_ip() + provider['path'] + '?'
        fields = {
            'application': self.application_name,
            'category': 'consumers',
            'check': 'false',
            'connected': 'true',
            'dubbo': provider_fields['dubbo'],
            'interface': provider_fields['interface'],
            'methods': provider_fields['methods'],
            'pid': get_pid(),
            'revision': provider_fields['revision'],
            'side': 'consumer',
            'timestamp': int(time.time() * 1000),
            'version': provider_fields['version'],
        }

        keys = fields.keys()
        keys.sort()
        for key in keys:
            value = fields[key]
            consumer += '{0}={1}&'.format(key, value)
        consumer = consumer[:-1]  # 干掉最后一个&

        consumer_path = DUBBO_ZK_CONSUMERS.format(fields['interface'])
        self.zk.ensure_path(consumer_path)
        self.zk.create_async(consumer_path + '/' + quote(consumer, safe=''), ephemeral=True)

    def close(self):
        self.zk.stop()


def parse_url(url_str):
    """
    把url字符串解析为适合于操作的对象
    :param url_str:
    :return:
    """
    url = urlparse(unquote(url_str))
    fields = dict(parse_qsl(url.query))
    result = {
        'scheme': url.scheme,
        'host': url.netloc,
        'hostname': url.hostname,
        'port': url.port,
        'path': url.path,
        'fields': fields
    }
    return result
