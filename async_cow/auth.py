# -*- coding: utf-8 -*-
from cachetools import TTLCache
import asyncio
import hmac
import json
import time

from hashlib import sha1
from qiniu import Auth
from urllib.parse import urlparse

from async_cow import config
from async_cow.compat import b
from async_cow.http.aio import CowClientRequest
from async_cow.http.base import RequestBase
from async_cow.service.storage.upload_progress_recorder import UploadProgressRecorder
from async_cow.utils import urlsafe_base64_encode, crc32, _file_iter, rfc_from_timestamp


TTL = 3500
CACHE_MAX_SIZE = 2000


class QiniuAuth(Auth):

    def __init__(self, access_key, secret_key, max_token_level=CACHE_MAX_SIZE):
        """
        :param access_key: access_key
        :param secret_key: secret_key
        :param max_token_level: token缓存数最大水位
        """
        super().__init__(access_key, secret_key)

        self._upload_token_cache = TTLCache(max_token_level, TTL)
        self._rtc_room_token_cache = TTLCache(max_token_level, TTL)

    def get_token(self,
                  bucket,
                  key=None,
                  policy=None,
                  strict_policy=True
                  ):

        token_key = f'{bucket}_{key}_{policy}_{strict_policy}'

        token = self._upload_token_cache.get(token_key, None)

        if not token:

            token = self.upload_token(bucket, key, expires=TTL + 100, policy=strict_policy, strict_policy=strict_policy)
            self._upload_token_cache[token_key] = token

        return token

    def get_rtc_room_token(self, room_access):

        if isinstance(room_access, dict) and 'deadline' in room_access:
            room_access['deadline'] = int(time.time()) + TTL + 100

        token_key = json.dumps(room_access)

        token = self._rtc_room_token_cache.get(token_key, None)

        if not token:

            token = self.token_with_data(token_key)
            self._rtc_room_token_cache[token_key] = token

        return token


class RequestsAuth:

    def __init__(self, auth):
        self.auth = auth

    def __call__(self, r):
        if r.body is not None and r.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            token = self.auth.token_of_request(
                r.url, r.body, 'application/x-www-form-urlencoded')
        else:
            token = self.auth.token_of_request(r.url)
        r.headers['Authorization'] = 'QBox {0}'.format(token)
        return r


class QiniuMacAuth(object):
    """
    Sign Requests

    Attributes:
        __access_key
        __secret_key

    http://kirk-docs.qiniu.com/apidocs/#TOC_325b437b89e8465e62e958cccc25c63f
    """

    def __init__(self, access_key, secret_key):
        self.qiniu_header_prefix = "X-Qiniu-"
        self.__checkKey(access_key, secret_key)
        self.__access_key = access_key
        self.__secret_key = b(secret_key)

    def __token(self, data):
        data = b(data)
        hashed = hmac.new(self.__secret_key, data, sha1)
        return urlsafe_base64_encode(hashed.digest())

    def token_of_request(
            self,
            method,
            host,
            url,
            qheaders,
            content_type=None,
            body=None):
        """
        <Method> <PathWithRawQuery>
        Host: <Host>
        Content-Type: <ContentType>
        [<X-Qiniu-*> Headers]

        [<Body>] #这里的 <Body> 只有在 <ContentType> 存在且不为 application/octet-stream 时才签进去。

        """
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc
        path = parsed_url.path
        query = parsed_url.query

        if not host:
            host = netloc

        path_with_query = path
        if query != '':
            path_with_query = ''.join([path_with_query, '?', query])
        data = ''.join(["%s %s" %
                        (method, path_with_query), "\n", "Host: %s" %
                        host, "\n"])

        if content_type:
            data += "Content-Type: %s" % (content_type) + "\n"

        data += qheaders
        data += "\n"

        if content_type and content_type != "application/octet-stream" and body:
            if isinstance(body, bytes):
                data += body.decode(encoding='UTF-8')
            else:
                data += body
        return '{0}:{1}'.format(self.__access_key, self.__token(data))

    def qiniu_headers(self, headers):
        res = ""
        for key in headers:
            if key.startswith(self.qiniu_header_prefix):
                res += key + ": %s\n" % (headers.get(key))
        return res

    @staticmethod
    def __checkKey(access_key, secret_key):
        if not (access_key and secret_key):
            raise ValueError('QiniuMacAuthSign : Invalid key')


class QiniuMacRequestsAuth:

    def __init__(self, auth):
        self.auth = auth

    def __call__(self, r: CowClientRequest):
        token = self.auth.token_of_request(
            r.method, r.headers.get('Host', None),
            r.url, self.auth.qiniu_headers(r.headers),
            r.headers.get('Content-Type', None),
            r.body
        )
        r.headers['Authorization'] = 'Qiniu {0}'.format(token)
        return r


class _Resume(object):
    """断点续上传类

    该类主要实现了分块上传，断点续上，以及相应地创建块和创建文件过程，详细规格参考：
    http://developer.qiniu.com/docs/v6/api/reference/up/mkblk.html
    http://developer.qiniu.com/docs/v6/api/reference/up/mkfile.html

    Attributes:
        up_token:                   上传凭证
        key:                        上传文件名
        input_stream:               上传二进制流
        data_size:                  上传流大小
        params:                     自定义变量，规格参考 http://developer.qiniu.com/docs/v6/api/overview/up/response/vars.html#xvar
        mime_type:                  上传数据的mimeType
        progress_handler:           上传进度
        upload_progress_recorder:   记录上传进度，用于断点续传
        modify_time:                上传文件修改日期
        hostscache_dir：            host请求 缓存文件保存位置
    """

    def __init__(self, up_token, key, input_stream, file_name, data_size, hostscache_dir, params, mime_type,
                 progress_handler, upload_progress_recorder, modify_time, keep_last_modified, **settings):
        """初始化断点续上传"""
        self.up_token = up_token
        self.key = key
        self.input_stream = input_stream
        self.file_name = file_name
        self.size = data_size
        self.hostscache_dir = hostscache_dir
        self.params = params
        self.mime_type = mime_type
        self.progress_handler = progress_handler
        self.upload_progress_recorder = upload_progress_recorder or UploadProgressRecorder()
        self.modify_time = modify_time or time.time()
        self.keep_last_modified = keep_last_modified

        if settings.get('http', None):
            self._http = settings.get('http', None)
        else:
            self._http = RequestBase(**settings)

    def record_upload_progress(self, offset):
        record_data = {
            'size': self.size,
            'offset': offset,
            'contexts': [block['ctx'] for block in self.blockStatus]
        }
        if self.modify_time:
            record_data['modify_time'] = self.modify_time

        self.upload_progress_recorder.set_upload_record(self.file_name, self.key, record_data)

    def recovery_from_record(self):
        record = self.upload_progress_recorder.get_upload_record(self.file_name, self.key)
        if not record:
            return 0

        try:
            if not record['modify_time'] or record['size'] != self.size or \
                    record['modify_time'] != self.modify_time:
                return 0
        except KeyError:
            return 0
        self.blockStatus = [{'ctx': ctx} for ctx in record['contexts']]
        return record['offset']

    async def upload(self):
        """上传操作"""
        self.blockStatus = []
        if config.get_default('default_zone').up_host:
            host = config.get_default('default_zone').up_host
        else:
            host = await config.get_default('default_zone').get_up_host_by_token(self.up_token, self.hostscache_dir)

        offset = self.recovery_from_record()
        async for block in _file_iter(self.input_stream, config._BLOCK_SIZE, offset):
            length = len(block)
            crc = crc32(block)
            ret, info = await self.make_block(block, length, host)
            if ret is None and not info.need_retry():
                return ret, info
            if info.connect_failed():
                if config.get_default('default_zone').up_host_backup:
                    host = config.get_default('default_zone').up_host_backup
                else:
                    host = await config.get_default('default_zone').get_up_host_backup_by_token(self.up_token,
                                                                                          self.hostscache_dir)
            if info.need_retry() or crc != ret['crc32']:
                ret, info = await self.make_block(block, length, host)
                if ret is None or crc != ret['crc32']:
                    return ret, info

            self.blockStatus.append(ret)
            offset += length
            self.record_upload_progress(offset)

            if asyncio.iscoroutinefunction(self.progress_handler):
                await self.progress_handler(((len(self.blockStatus) - 1) * config._BLOCK_SIZE) + length, self.size)
            elif (callable(self.progress_handler)):
                self.progress_handler(((len(self.blockStatus) - 1) * config._BLOCK_SIZE) + length, self.size)

        return await self.make_file(host)

    async def make_block(self, block, block_size, host):
        """创建块"""
        url = self.block_url(host, block_size)
        return await self.post(url, block)

    def block_url(self, host, size):
        return '{0}/mkblk/{1}'.format(host, size)

    def file_url(self, host):
        url = ['{0}/mkfile/{1}'.format(host, self.size)]

        if self.mime_type:
            url.append('mimeType/{0}'.format(urlsafe_base64_encode(self.mime_type)))

        if self.key is not None:
            url.append('key/{0}'.format(urlsafe_base64_encode(self.key)))

        if self.file_name is not None:
            url.append('fname/{0}'.format(urlsafe_base64_encode(self.file_name)))

        if self.params:
            for k, v in self.params.items():
                url.append('{0}/{1}'.format(k, urlsafe_base64_encode(v)))
            pass

        if self.modify_time and self.keep_last_modified:
            url.append(
                "x-qn-meta-!Last-Modified/{0}".format(urlsafe_base64_encode(rfc_from_timestamp(self.modify_time))))

        url = '/'.join(url)
        # print url
        return url

    async def make_file(self, host):
        """创建文件"""
        url = self.file_url(host)
        body = ','.join([status['ctx'] for status in self.blockStatus])
        self.upload_progress_recorder.delete_upload_record(self.file_name, self.key)
        return await self.post(url, body)

    async def post(self, url, data):
        return await self._http._post_with_token(url, data, self.up_token)
