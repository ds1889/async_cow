# -*- coding: utf-8 -*-


class RtcServer(object):
    """
    直播连麦管理类
    主要涉及了直播连麦管理及操作接口的实现，和官方SDK接口同步，具体的接口规格可以参考官方文档 https://developer.qiniu.com
    TODO 所有功能方法都将返回协程对象，必须用await调用，和原七牛SDK保持接口同步
    Attributes:
        cow: AsyncCow对象
        不希望你直接调用本类
        而是通过下列方式调用

        server = AsyncCow(<access_key>, <secret_key>).get_rtc_server()
        res = await server.create_app(<data>)
    """

    def __init__(self, cow):
        self.cow = cow
        self.host = 'http://rtc.qiniuapi.com'

    def create_app(self, data):
        return self._post(self.host + '/v3/apps', data)

    def get_app(self, app_id=None):
        if app_id:
            return self._get(self.host + '/v3/apps/%s' % app_id)
        else:
            return self._get(self.host + '/v3/apps')

    def delete_app(self, app_id):
        return self._delete(self.host + '/v3/apps/%s' % app_id)

    def update_app(self, app_id, data):
        return self._post(self.host + '/v3/apps/%s' % app_id, data)

    def list_user(self, app_id, room_name):
        return self._get(self.host + '/v3/apps/%s/rooms/%s/users' % (app_id, room_name))

    def kick_user(self, app_id, room_name, user_id):
        return self._delete(self.host + '/v3/apps/%s/rooms/%s/users/%s' % (app_id, room_name, user_id))

    def list_active_rooms(self, app_id, room_name_prefix=None):
        if room_name_prefix:
            return self._get(self.host + '/v3/apps/%s/rooms?prefix=%s' % (app_id, room_name_prefix))
        else:
            return self._get(self.host + '/v3/apps/%s/rooms' % app_id)

    def _post(self, url, data=None):
        return self.cow._http._post_with_qiniu_mac(url, data, self.cow._auth)

    def _get(self, url, params=None):
        return self.cow._http._get_with_qiniu_mac(url, params, self.cow._auth)

    def _delete(self, url, params=None):
        return self.cow._http._delete_with_qiniu_mac(url, params, self.cow._auth)
