# -*- coding: utf-8 -*-

import os
import time
from async_cow import compat
from async_cow import utils
from async_cow.http.aio import HTTPClient, CowClientRequest

UC_HOST = 'https://uc.qbox.me'  # 获取空间信息Host


class Region(object):
    """七牛上传区域类

    该类主要内容上传区域地址。

    """

    def __init__(
            self,
            up_host=None,
            up_host_backup=None,
            io_host=None,
            host_cache={},
            home_dir=None,
            scheme="http"):
        """初始化Zone类"""
        self.up_host, self.up_host_backup, self.io_host, self.home_dir = up_host, up_host_backup, io_host, home_dir
        self.host_cache = host_cache
        self.scheme = scheme

    async def get_up_host_by_token(self, up_token, home_dir):
        ak, bucket = self.unmarshal_up_token(up_token)
        if home_dir is None:
            home_dir = os.getcwd()
        up_hosts = await self.get_up_host(ak, bucket, home_dir)
        return up_hosts[0]

    async def get_up_host_backup_by_token(self, up_token, home_dir):
        ak, bucket = self.unmarshal_up_token(up_token)
        if home_dir is None:
            home_dir = os.getcwd()
        up_hosts = await self.get_up_host(ak, bucket, home_dir)
        if (len(up_hosts) <= 1):
            up_host = up_hosts[0]
        else:
            up_host = up_hosts[1]
        return up_host

    async def get_io_host(self, ak, bucket, home_dir):
        if self.io_host:
            return self.io_host
        if home_dir is None:
            home_dir = os.getcwd()
        bucket_hosts = await self.get_bucket_hosts(ak, bucket, home_dir)
        io_hosts = bucket_hosts['ioHosts']
        return io_hosts[0]

    async def get_up_host(self, ak, bucket, home_dir):
        bucket_hosts = await self.get_bucket_hosts(ak, bucket, home_dir)
        up_hosts = bucket_hosts['upHosts']
        return up_hosts

    def unmarshal_up_token(self, up_token):
        token = up_token.split(':')
        if (len(token) != 3):
            raise ValueError('invalid up_token')

        ak = token[0]
        policy = compat.json.loads(
            compat.s(
                utils.urlsafe_base64_decode(
                    token[2])))

        scope = policy["scope"]
        bucket = scope
        if (':' in scope):
            bucket = scope.split(':')[0]

        return ak, bucket

    async def get_bucket_hosts(self, ak, bucket, home_dir):
        key = self.scheme + ":" + ak + ":" + bucket

        bucket_hosts = self.get_bucket_hosts_to_cache(key, home_dir)
        if (len(bucket_hosts) > 0):
            return bucket_hosts

        hosts = {}
        hosts.update({self.scheme: {}})

        hosts[self.scheme].update({'up': []})
        hosts[self.scheme].update({'io': []})

        if self.up_host is not None:
            hosts[self.scheme]['up'].append(self.scheme + "://" + self.up_host)

        if self.up_host_backup is not None:
            hosts[self.scheme]['up'].append(
                self.scheme + "://" + self.up_host_backup)

        if self.io_host is not None:
            hosts[self.scheme]['io'].append(self.scheme + "://" + self.io_host)

        if len(hosts[self.scheme]) == 0 or self.io_host is None:
            hosts = compat.json.loads(await self.bucket_hosts(ak, bucket))
        else:
            # 1 year
            hosts['ttl'] = int(time.time()) + 31536000
        try:
            scheme_hosts = hosts[self.scheme]
        except KeyError:
            raise KeyError(
                "Please check your BUCKET_NAME! The UpHosts is %s" %
                hosts)
        bucket_hosts = {
            'upHosts': scheme_hosts['up'],
            'ioHosts': scheme_hosts['io'],
            'deadline': int(time.time()) + hosts['ttl']
        }
        home_dir = ""
        self.set_bucket_hosts_to_cache(key, bucket_hosts, home_dir)
        return bucket_hosts

    def get_bucket_hosts_to_cache(self, key, home_dir):
        ret = []
        if (len(self.host_cache) == 0):
            self.host_cache_from_file(home_dir)

        if (not (key in self.host_cache)):
            return ret

        if (self.host_cache[key]['deadline'] > time.time()):
            ret = self.host_cache[key]

        return ret

    def set_bucket_hosts_to_cache(self, key, val, home_dir):
        self.host_cache[key] = val
        self.host_cache_to_file(home_dir)
        return

    def host_cache_from_file(self, home_dir):
        if home_dir is not None:
            self.home_dir = home_dir
        path = self.host_cache_file_path()
        if not os.path.isfile(path):
            return None
        with open(path, 'r') as f:
            bucket_hosts = compat.json.load(f)
            self.host_cache = bucket_hosts
        f.close()
        return

    def host_cache_file_path(self):
        return os.path.join(self.home_dir, ".qiniu_pythonsdk_hostscache.json")

    def host_cache_to_file(self, home_dir):
        path = self.host_cache_file_path()
        dir, file = os.path.split(path)

        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(path, 'w') as f:
            compat.json.dump(self.host_cache, f)
        f.close()

    async def bucket_hosts(self, ak, bucket):

        url = "{0}/v1/query?ak={1}&bucket={2}".format(UC_HOST, ak, bucket)
        ret = await HTTPClient(request_class=CowClientRequest).get(url)
        data = compat.json.dumps(ret.json(), separators=(',', ':'))
        return data
