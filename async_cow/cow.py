# -*- coding: utf-8 -*-

import os

from async_cow import config
from async_cow.auth import QiniuAuth, _Resume, QiniuMacAuth
from async_cow.http.base import RequestBase
from async_cow.service.cdn.manager import CdnManager, DomainManager
from async_cow.service.compute.app import AccountClient
from async_cow.service.compute.qcos_api import QcosClient
from async_cow.service.pili.rtc_server_manager import RtcServer
from async_cow.service.processing.pfop import PersistentFop
from async_cow.service.storage.bucket import Bucket
from async_cow.service.sms.sms import Sms
from async_cow.utils import crc32, file_crc32, rfc_from_timestamp


class AsyncCow:

    def __init__(self, access_key, secret_key, max_token_level=None, **settings):

        self._auth = QiniuAuth(access_key, secret_key, max_token_level)

        self._http = RequestBase(**settings)

    @property
    def http(self):

        return self._http

    @property
    def auth(self):

        return self.auth

    def get_bucket(self, bucket):
        """
        推荐使用此方法得到一个bucket对象,
        对一个bucket的文件进行操作
        然后对此bucket的操作就只用传递文件名即可
        """
        return Bucket(self, bucket)

    def get_sms(self):
        """
        获取一个sms客户端对象，可以用该对象操作原七牛SDK中Sms对象的所有功能
        该对象的所有功能方法将返回协程对象，须await调用
        :return: object Sms
        """
        return Sms(self)

    def get_rtc_server(self):
        """
        获取直播连麦管理client
        """
        return RtcServer(self)

    def get_persistent_fop(self, bucket, pipeline=None, notify_url=None):
        """
        获取持久化处理对象
        该类用于主动触发异步持久化操作
        """
        return PersistentFop(self, bucket, pipeline, notify_url)

    def get_cdn_manager(self):
        """获取cdn管理对象"""

        return CdnManager(self)

    def get_domain_manager(self):
        """获取域名管理对象"""
        return DomainManager(self)

    def get_token(self,
                  bucket,
                  key=None,
                  policy=None,
                  strict_policy=True
                  ):
        """
        生成上传凭证

        Args:
            bucket:  上传的空间名
            key:     上传的文件名，默认为空
            policy:  上传策略，默认为空

        Returns:
            上传凭证
        """
        return self._auth.get_token(bucket, key, policy, strict_policy)

    def get_rtc_room_token(self, room_access):
        """
        获取直播房间token
        同官方SDK中 get_room_token 加以缓存管理
        from qiniu.services.pili.rtc_server_manager import get_room_token
        """
        return self._auth.get_rtc_room_token(room_access)

    async def put_data(self,
                       up_token,
                       key,
                       data,
                       params=None,
                       mime_type='application/octet-stream',
                       check_crc=False,
                       progress_handler=None,
                       fname=None,
                       hostscache_dir=None):
        """上传二进制流到七牛

        Args:
            up_token:         上传凭证
            key:              上传文件名
            data:             上传二进制流
            params:           自定义变量，规格参考 http://developer.qiniu.com/docs/v6/api/overview/up/response/vars.html#xvar
            mime_type:        上传数据的mimeType
            check_crc:        是否校验crc32
            progress_handler: 上传进度回调函数，可以是协程函数，也可以是普通函数或方法
            hostscache_dir：  host请求 缓存文件保存位置

        Returns:
            一个dict变量，类似 {"hash": "<Hash string>", "key": "<Key string>"}
            一个ResponseInfo对象
        """

        final_data = b''
        if hasattr(data, 'read'):
            while True:
                tmp_data = data.read(config._BLOCK_SIZE)
                if len(tmp_data) == 0:
                    break
                else:
                    final_data += tmp_data
        else:
            final_data = data

        crc = crc32(final_data)
        return await self._form_put(up_token, key, final_data, params, mime_type, crc, hostscache_dir, progress_handler,
                                    fname)

    async def put_file(self,
                       up_token,
                       key,
                       file_path,
                       params=None,
                       mime_type='application/octet-stream',
                       check_crc=False,
                       progress_handler=None,
                       upload_progress_recorder=None,
                       keep_last_modified=False,
                       hostscache_dir=None):

        """上传文件到七牛

        Args:
            up_token:                 上传凭证
            key:                      上传文件名
            file_path:                上传文件的路径
            params:                   自定义变量，规格参考 http://developer.qiniu.com/docs/v6/api/overview/up/response/vars.html#xvar
            mime_type:                上传数据的mimeType
            check_crc:                是否校验crc32
            progress_handler:         上传进度，可以是协程函数，也可以是普通函数或方法
            upload_progress_recorder: 记录上传进度，用于断点续传
            hostscache_dir：          host请求 缓存文件保存位置

        Returns:
            一个dict变量，类似 {"hash": "<Hash string>", "key": "<Key string>"}
            一个ResponseInfo对象
        """
        ret = {}
        size = os.stat(file_path).st_size
        import aiofiles
        async with aiofiles.open(file_path, mode='rb') as input_stream:
            # with open(file_path, 'rb') as input_stream:
            file_name = os.path.basename(file_path)
            modify_time = int(os.path.getmtime(file_path))
            if size > config._BLOCK_SIZE * 2:
                ret, info = await self.put_stream(up_token, key, input_stream, file_name, size, hostscache_dir, params,
                                                  mime_type, progress_handler,
                                                  upload_progress_recorder=upload_progress_recorder,
                                                  modify_time=modify_time, keep_last_modified=keep_last_modified)
            else:
                crc = file_crc32(file_path)
                ret, info = await self._form_put(up_token, key, input_stream, params, mime_type,
                                                 crc, hostscache_dir, progress_handler, file_name,
                                                 modify_time=modify_time, keep_last_modified=keep_last_modified)
        return ret, info

    async def _form_put(self, up_token, key, data, params, mime_type, crc, hostscache_dir=None, progress_handler=None,
                        file_name=None,
                        modify_time=None,
                        keep_last_modified=False):
        fields = {}
        if params:
            for k, v in params.items():
                fields[k] = str(v)
        if crc:
            fields['crc32'] = crc
        if key is not None:
            fields['key'] = key

        fields['token'] = up_token
        if config.get_default('default_zone').up_host:
            url = config.get_default('default_zone').up_host
        else:
            url = await config.get_default('default_zone').get_up_host_by_token(up_token, hostscache_dir)
        # name = key if key else file_name

        fname = file_name
        if not fname or not fname.strip():
            fname = 'file_name'

        # last modify time
        if modify_time and keep_last_modified:
            fields['x-qn-meta-!Last-Modified'] = rfc_from_timestamp(modify_time)

        r, info = await self._http._post_file(url, data=fields, files={'file': (fname, data, mime_type)})
        if r is None and info.need_retry():
            if info.connect_failed:
                if config.get_default('default_zone').up_host_backup:
                    url = config.get_default('default_zone').up_host_backup
                else:
                    url = await config.get_default('default_zone').get_up_host_backup_by_token(up_token, hostscache_dir)
            if hasattr(data, 'read') is False:
                pass
            elif hasattr(data, 'seek') and (not hasattr(data, 'seekable') or data.seekable()):
                data.seek(0)
            else:
                return r, info
            r, info = await self._http._post_file(url, data=fields, files={'file': (fname, data, mime_type)})

        return r, info

    async def put_stream(self,
                         up_token,
                         key,
                         input_stream,
                         file_name,
                         data_size,
                         hostscache_dir=None,
                         params=None,
                         mime_type=None,
                         progress_handler=None,
                         upload_progress_recorder=None,
                         modify_time=None,
                         keep_last_modified=False):

        task = _Resume(up_token, key, input_stream, file_name, data_size, hostscache_dir, params, mime_type,
                       progress_handler, upload_progress_recorder, modify_time, keep_last_modified)
        return await task.upload()


class ClientCow:

    def __init__(self, access_key, secret_key, auth_class=QiniuMacAuth, **settings):

        if issubclass(auth_class, QiniuMacAuth):
            self._auth = auth_class(access_key, secret_key)
        else:
            self._auth = None

        self._http = RequestBase(**settings)

    @property
    def http(self):

        return self._http

    @property
    def auth(self):

        return self.auth

    def get_app(self):
        """
        账号客户端
        auth=None，会自动使用 apiproxy 服务
        """
        return AccountClient(self)

    def get_qcos_client(self):
        """
        资源管理客户端
        self.auth=None，会自动使用 apiproxy 服务，只能管理当前容器所在的应用资源。
        """
        return QcosClient(self)


