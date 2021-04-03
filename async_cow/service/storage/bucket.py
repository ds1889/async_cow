# -*- coding: utf-8 -*-

from async_cow import config
from async_cow.utils import urlsafe_base64_encode, entry


class Bucket(object):
    """空间管理类

    主要涉及了空间资源管理及批量操作接口的实现，具体的接口规格可以参考：
    http://developer.qiniu.com/docs/v6/api/reference/rs/

    Attributes:
        auth: 账号管理密钥对，Auth对象
    """

    def __init__(self, cow, bucket, zone=None):
        self._cow = cow
        self._bucket = bucket
        if (zone is None):
            self.zone = config.get_default('default_zone')
        else:
            self.zone = zone

    async def put_data(self,
                       key,
                       data,
                       params=None,
                       mime_type='application/octet-stream',
                       check_crc=False,
                       progress_handler=None,
                       fname=None,
                       hostscache_dir=None):

        token = self._cow.get_token(
            self._bucket, key
        )

        return await self._cow.put_data(token, key, data, params, mime_type, check_crc, progress_handler, fname,
                                        hostscache_dir)

    async def put_file(self,
                       key,
                       file_path,
                       params=None,
                       mime_type='application/octet-stream',
                       check_crc=False,
                       progress_handler=None,
                       upload_progress_recorder=None,
                       keep_last_modified=False,
                       hostscache_dir=None):

        token = self._cow.get_token(
            self._bucket, key
        )

        return await self._cow.put_file(token, key, file_path, params, mime_type, check_crc, progress_handler,
                                        upload_progress_recorder, keep_last_modified, hostscache_dir)

    async def put_stream(self,
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

        token = self._cow.get_token(
            self._bucket, key
        )
        return await self._cow.put_stream(token, key, input_stream, file_name, data_size, hostscache_dir, params,
                                          mime_type, progress_handler, upload_progress_recorder, modify_time,
                                          keep_last_modified)

    async def list(self, prefix=None, marker=None, limit=None, delimiter=None):
        """前缀查询:

        1. 首次请求 marker = None
        2. 无论 err 值如何，均应该先看 ret.get('items') 是否有内容
        3. 如果后续没有更多数据，err 返回 EOF，marker 返回 None（但不通过该特征来判断是否结束）
        具体规格参考:
        http://developer.qiniu.com/docs/v6/api/reference/rs/list.html

        Args:
            prefix:     列举前缀
            marker:     列举标识符
            limit:      单次列举个数限制
            delimiter:  指定目录分隔符

        Returns:
            一个dict变量，类似 {"hash": "<Hash string>", "key": "<Key string>"}
            一个ResponseInfo对象
            一个EOF信息。
        """
        options = {
            'bucket': self._bucket,
        }
        if marker is not None:
            options['marker'] = marker
        if limit is not None:
            options['limit'] = limit
        if prefix is not None:
            options['prefix'] = prefix
        if delimiter is not None:
            options['delimiter'] = delimiter

        url = '{0}/list'.format(config.get_default('default_rsf_host'))
        ret, info = await self._get(url, options)

        eof = False
        if ret and not ret.get('marker'):
            eof = True

        return ret, eof, info

    async def stat(self, key):
        """获取文件信息:

        获取资源的元信息，但不返回文件内容，具体规格参考：
        https://developer.qiniu.com/kodo/api/1308/stat

        Args:
            bucket: 待获取信息资源所在的空间
            key:    待获取资源的文件名

        Returns:
            一个dict变量，类似：
                {
                    "fsize":        5122935,
                    "hash":         "ljfockr0lOil_bZfyaI2ZY78HWoH",
                    "mimeType":     "application/octet-stream",
                    "putTime":      13603956734587420
                    "type":         0
                }
            一个ResponseInfo对象
        """
        resource = entry(self._bucket, key)
        return await self._rs_do('stat', resource)

    async def delete(self, key):
        """删除文件:

        删除指定资源，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/delete.html

        Args:
            bucket: 待获取信息资源所在的空间
            key:    待获取资源的文件名

        Returns:
            一个dict变量，成功返回NULL，失败返回{"error": "<errMsg string>"}
            一个ResponseInfo对象
        """
        resource = entry(self._bucket, key)
        return await self._rs_do('delete', resource)

    async def rename(self, key, key_to, force='false'):
        """重命名文件:

        给资源进行重命名，本质为move操作。

        Args:
            key:    待操作资源文件名
            key_to: 目标资源文件名

        Returns:
            一个dict变量，成功返回NULL，失败返回{"error": "<errMsg string>"}
            一个ResponseInfo对象
        """
        return await self.move(key, self._bucket, key_to, force)

    async def move(self, key, bucket_to=None, key_to=None, force='false'):
        """移动文件:

        将资源从一个空间到另一个空间，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/move.html

        Args:
            bucket:     待操作资源所在空间
            bucket_to:  目标资源空间名
            key:        待操作资源文件名
            key_to:     目标资源文件名

        Returns:
            一个dict变量，成功返回NULL，失败返回{"error": "<errMsg string>"}
            一个ResponseInfo对象
        """

        resource = entry(self._bucket, key)
        to = entry(bucket_to if bucket_to else self._bucket, key_to if key_to else key)
        return await self._rs_do('move', resource, to, 'force/{0}'.format(force))

    async def copy(self, key, bucket_to, key_to, force='false'):
        """复制文件:

        将指定资源复制为新命名资源，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/copy.html

        Args:
            bucket:     待操作资源所在空间
            bucket_to:  目标资源空间名
            key:        待操作资源文件名
            key_to:     目标资源文件名

        Returns:
            一个dict变量，成功返回NULL，失败返回{"error": "<errMsg string>"}
            一个ResponseInfo对象
        """
        resource = entry(self._bucket, key)
        to = entry(bucket_to, key_to)
        return await self._rs_do('copy', resource, to, 'force/{0}'.format(force))

    async def fetch(self, url, key=None, hostscache_dir=None):
        """抓取文件:
        从指定URL抓取资源，并将该资源存储到指定空间中，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/fetch.html

        Args:
            url:      指定的URL
            bucket:   目标资源空间
            key:      目标资源文件名
            hostscache_dir： host请求 缓存文件保存位置

        Returns:
            一个dict变量：
                成功 返回{'fsize': <fsize int>, 'hash': <hash string>, 'key': <key string>, 'mimeType': <mimeType string>}
                失败 返回 None
            一个ResponseInfo对象
        """
        resource = urlsafe_base64_encode(url)
        to = entry(self._bucket, key)
        return await self._io_do(self._bucket, 'fetch', hostscache_dir, resource, 'to/{0}'.format(to))

    async def prefetch(self, key, hostscache_dir=None):
        """镜像回源预取文件:

        从镜像源站抓取资源到空间中，如果空间中已经存在，则覆盖该资源，具体规格参考
        http://developer.qiniu.com/docs/v6/api/reference/rs/prefetch.html

        Args:
            bucket: 待获取资源所在的空间
            key:    代获取资源文件名
            hostscache_dir： host请求 缓存文件保存位置

        Returns:
            一个dict变量，成功返回NULL，失败返回{"error": "<errMsg string>"}
            一个ResponseInfo对象
        """
        resource = entry(self._bucket, key)
        return await self._io_do(self._bucket, 'prefetch', hostscache_dir, resource)

    async def change_mime(self, key, mime):
        """修改文件mimeType:

        主动修改指定资源的文件类型，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/chgm.html

        Args:
            bucket: 待操作资源所在空间
            key:    待操作资源文件名
            mime:   待操作文件目标mimeType
        """
        resource = entry(self._bucket, key)
        encode_mime = urlsafe_base64_encode(mime)
        return await self._rs_do('chgm', resource, 'mime/{0}'.format(encode_mime))

    async def change_type(self, key, storage_type):
        """修改文件的存储类型

        修改文件的存储类型为普通存储或者是低频存储，参考文档：
        https://developer.qiniu.com/kodo/api/3710/modify-the-file-type

        Args:
            bucket:         待操作资源所在空间
            key:            待操作资源文件名
            storage_type:   待操作资源存储类型，0为普通存储，1为低频存储，2 为归档存储
        """
        resource = entry(self._bucket, key)
        return await self._rs_do('chtype', resource, 'type/{0}'.format(storage_type))

    async def restoreAr(self, key, freezeAfter_days):
        """解冻归档存储文件

        修改文件的存储类型为普通存储或者是低频存储，参考文档：
        https://developer.qiniu.com/kodo/api/6380/restore-archive

        Args:
            bucket:         待操作资源所在空间
            key:            待操作资源文件名
            freezeAfter_days:   解冻有效时长，取值范围 1～7
        """
        resource = entry(self._bucket, key)
        return await self._rs_do('restoreAr', resource, 'freezeAfterDays/{0}'.format(freezeAfter_days))

    async def change_status(self, key, status, cond):
        """修改文件的状态

        修改文件的存储类型为可用或禁用：

        Args:
            bucket:         待操作资源所在空间
            key:            待操作资源文件名
            storage_type:   待操作资源存储类型，0为启用，1为禁用
        """
        resource = entry(self._bucket, key)
        if cond and isinstance(cond, dict):
            condstr = ""
            for k, v in cond.items():
                condstr += "{0}={1}&".format(k, v)
            condstr = urlsafe_base64_encode(condstr[:-1])
            return await self._rs_do('chstatus', resource, 'status/{0}'.format(status), 'cond', condstr)
        return await self._rs_do('chstatus', resource, 'status/{0}'.format(status))

    async def batch(self, operations):
        """批量操作:

        在单次请求中进行多个资源管理操作，具体规格参考：
        http://developer.qiniu.com/docs/v6/api/reference/rs/batch.html

        Args:
            operations: 资源管理操作数组，可通过

        Returns:
            一个dict变量，返回结果类似：
                [
                    { "code": <HttpCode int>, "data": <Data> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int>, "data": { "error": "<ErrorMessage string>" } },
                    ...
                ]
            一个ResponseInfo对象
        """
        url = '{0}/batch'.format(config.get_default('default_rs_host'))
        return await self._post(url, dict(op=operations))

    async def buckets(self):
        """获取所有空间名:

        获取指定账号下所有的空间名。

        Returns:
            一个dict变量，类似：
                [ <Bucket1>, <Bucket2>, ... ]
            一个ResponseInfo对象
        """
        return await self._rs_do('buckets')

    async def delete_after_days(self, key, days):
        """更新文件生命周期

        Returns:
            一个dict变量，返回结果类似：
                [
                    { "code": <HttpCode int>, "data": <Data> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int> },
                    { "code": <HttpCode int>, "data": { "error": "<ErrorMessage string>" } },
                    ...
                ]
            一个ResponseInfo对象
        Args:
            key:    目标资源文件名
            days:   指定天数
        """
        if isinstance(days, int):
            days = str(days)
        resource = entry(self._bucket, key)
        return await self._rs_do('deleteAfterDays', resource, days)

    async def mkbucketv3(self, bucket_name, region):
        """
        创建存储空间，全局唯一，其他账号有同名空间就无法创建

        Args:
            bucket_name: 存储空间名
            region: 存储区域
        """
        return await self._rs_do('mkbucketv3', bucket_name, 'region', region)

    async def list_bucket(self, region):
        """
        列举存储空间列表

        Args:
        """
        return await self._uc_do('v3/buckets?region={0}'.format(region))

    async def bucket_info(self, bucket_name=None):
        """
        获取存储空间信息

        Args:
            bucket_name: 存储空间名
        """
        if not bucket_name:
            bucket_name = self._bucket
        return await self._uc_do('v2/bucketInfo?bucket={}'.format(bucket_name), )

    async def bucket_domain(self, bucket_name=None):
        """
        获取存储空间域名列表
        Args:
            bucket_name: 存储空间名
        """
        if not bucket_name:
            bucket_name = self._bucket
        options = {
            'tbl': bucket_name,
        }
        url = "{0}/v6/domain/list?tbl={1}".format(config.get_default("default_api_host"), bucket_name)
        return await self._get(url, options)

    async def change_bucket_permission(self, bucket_name=None, private=1):
        """
        设置 存储空间访问权限
        https://developer.qiniu.com/kodo/api/3946/set-bucket-private
        Args:
            bucket_name: 存储空间名
            private: 0 公开；1 私有 ,str类型
        """
        if not bucket_name:
            bucket_name = self._bucket
        url = "{0}/private?bucket={1}&private={2}".format(config.get_default("default_uc_host"), bucket_name, private)
        return await self._post(url)

    async def _uc_do(self, operation, *args):
        return await self._server_do(config.get_default('default_uc_host'), operation, *args)

    async def _rs_do(self, operation, *args):
        return await self._server_do(config.get_default('default_rs_host'), operation, *args)

    async def _io_do(self, bucket, operation, home_dir, *args):
        ak = self._cow.get_access_key()
        io_host = await self.zone.get_io_host(ak, bucket, home_dir)
        return await self._server_do(io_host, operation, *args)

    async def _server_do(self, host, operation, *args):
        cmd = self._build_op(operation, *args)
        url = '{0}/{1}'.format(host, cmd)
        return await self._post(url)

    async def _post(self, url, data=None):
        return await self._cow.http._post_with_auth(url, data, self._cow.auth)

    async def _get(self, url, params=None):
        return await self._cow.http._get_with_auth(url, params, self._cow.auth)

    @classmethod
    def _build_op(cls, *args):
        return '/'.join(args)

    @classmethod
    def build_batch_copy(cls, source_bucket, key_pairs, target_bucket, force='false'):
        return cls._two_key_batch('copy', source_bucket, key_pairs, target_bucket, force)

    @classmethod
    def build_batch_rename(cls, bucket, key_pairs, force='false'):
        return cls.build_batch_move(bucket, key_pairs, bucket, force)

    @classmethod
    def build_batch_move(cls, source_bucket, key_pairs, target_bucket, force='false'):
        return cls._two_key_batch('move', source_bucket, key_pairs, target_bucket, force)

    @classmethod
    def build_batch_restoreAr(cls, bucket, keys):
        return cls._three_key_batch('restoreAr', bucket, keys)

    @classmethod
    def build_batch_delete(cls, bucket, keys):
        return cls._one_key_batch('delete', bucket, keys)

    @classmethod
    def build_batch_stat(cls, bucket, keys):
        return cls._one_key_batch('stat', bucket, keys)
    
    @classmethod
    def _one_key_batch(cls, operation, bucket, keys):
        return [cls._build_op(operation, entry(bucket, key)) for key in keys]
    
    @classmethod
    def _two_key_batch(cls, operation, source_bucket, key_pairs, target_bucket, force='false'):
        if target_bucket is None:
            target_bucket = source_bucket
        return [cls._build_op(operation, entry(source_bucket, k), entry(target_bucket, v), 'force/{0}'.format(force)) for k, v
                in key_pairs.items()]
    
    @classmethod
    def _three_key_batch(cls, operation, bucket, keys):
        return [cls._build_op(operation, entry(bucket, k), 'freezeAfterDays/{0}'.format(v)) for k, v
                in keys.items()]
