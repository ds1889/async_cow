# -*- coding: utf-8 -*-

from qiniu import config
from qiniu import http


class PersistentFop(object):
    """持久化处理类
    所有功能方法都将返回协程对象，必须用await调用，和原七牛SDK保持接口同步

    该类用于主动触发异步持久化操作，具体规格参考：
    http://developer.qiniu.com/docs/v6/api/reference/fop/pfop/pfop.html

    Attributes:
        cow:        AsyncCow对象
        bucket:     操作资源所在空间
        pipeline:   多媒体处理队列，详见 https://portal.qiniu.com/mps/pipeline
        notify_url: 持久化处理结果通知URL

        不希望你直接调用本类
        而是通过下列方式调用

        server = AsyncCow(<access_key>, <secret_key>).get_rtc_server()
        res = await server.create_app(<data>)
    """

    def __init__(self, cow, bucket, pipeline=None, notify_url=None):
        """初始化持久化处理类"""
        self.cow = cow
        self.bucket = bucket
        self.pipeline = pipeline
        self.notify_url = notify_url

    def execute(self, key, fops, force=None):
        """执行持久化处理:

        Args:
            key:    待处理的源文件
            fops:   处理详细操作，规格详见 https://developer.qiniu.com/dora/manual/1291/persistent-data-processing-pfop
            force:  强制执行持久化处理开关

        Returns:
            一个dict变量，返回持久化处理的persistentId，类似{"persistentId": 5476bedf7823de4068253bae};
            一个ResponseInfo对象
        """
        ops = ';'.join(fops)
        data = {'bucket': self.bucket, 'key': key, 'fops': ops}
        if self.pipeline:
            data['pipeline'] = self.pipeline
        if self.notify_url:
            data['notifyURL'] = self.notify_url
        if force == 1:
            data['force'] = 1

        url = '{0}/pfop'.format(config.get_default('default_api_host'))
        return self.cow.http._post_with_auth(url, data, self.cow.auth)
