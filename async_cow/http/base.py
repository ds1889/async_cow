# -*- coding: utf-8 -*-

import platform
import functools
import traceback

from aiohttp import FormData
from qiniu.http import ResponseInfo
from async_cow.http.aio import CowClientRequest, logger, HTTPClientPool, CowHttpAuthBase, HTTPClient

_sys_info = '{0}; {1}'.format(platform.system(), platform.machine())

USER_AGENT = 'QiniuPython/7.3.1 ({0}; ) Python/{1}'.format(_sys_info, platform.python_version())


def return_wrapper(func):

    @functools.wraps(func)
    async def _wrapper(*args, **kwargs):
        try:
            resp = await func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            return None, ResponseInfo(None, e)
        
        if resp.status != 200 or resp.headers.get('X-Reqid') is None:
            return None, ResponseInfo(resp)

        resp.encoding = 'utf-8'

        ret = resp.json() if resp.text() != '' else {}
        return ret, ResponseInfo(resp)

    return _wrapper


class RequestBase:

    def __init__(self, **setting):

        # self._http_client_pool = HTTPClientPool(request_class=CowClientRequest, **setting)
        self._setting = setting
        self._headers = {'User-Agent': USER_AGENT}

    @return_wrapper
    async def _post(self, url, data, files, auth, headers=None):

        post_headers = self._headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})

        if isinstance(data, dict):
            form = FormData()
            for k, v in data.items():
                form.add_field(k, str(v))

            if files:
                form.add_field('file', files['file'][1], filename=files['file'][0])

        else:
            form = data

        resp = await HTTPClient(request_class=CowClientRequest, **self._setting).post(
            url,
            data=form,
            auth=auth,
            headers=post_headers
        )

        return resp
    
    @return_wrapper
    async def _put(self, url, data, files, auth, headers=None):

        post_headers = self._headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})

        if isinstance(data, dict):
            form = FormData()
            for k, v in data.items():
                form.add_field(k, str(v))

            if files:
                form.add_field('file', files['file'][1], filename=files['file'][0])

        else:
            form = data

        resp = await HTTPClient(request_class=CowClientRequest, **self._setting).put(
            url,
            data=form,
            auth=auth,
            headers=post_headers
        )

        return resp

    @return_wrapper
    async def _get(self, url, params, auth, headers=None):

        post_headers = self._headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})

        resp = await HTTPClient(request_class=CowClientRequest, **self._setting).get(
            url,
            params=params,
            auth=auth,
            headers=post_headers
        )
        return resp

    def _post_with_token(self, url, data, token):
        return self._post(url, data, None, _TokenAuth(token))

    def _post_file(self, url, data, files):
        return self._post(url, data, files, None)

    def _post_with_auth(self, url, data, auth):
        return self._post(url, data, None, RequestsAuth(auth))

    def _get_with_auth(self, url, data, auth):
        return self._get(url, data, RequestsAuth(auth))

    def _post_with_auth_and_headers(self, url, data, auth, headers):
        return self._post(url, data, None, RequestsAuth(auth), headers)

    def _get_with_auth_and_headers(self, url, data, auth, headers):
        return self._get(url, data, RequestsAuth(auth), headers)

    def _post_with_qiniu_mac_and_headers(self, url, data, auth, headers):
        return self._post(url, data, None, QiniuMacRequestsAuth(auth), headers)

    def _put_with_auth(self, url, data, auth):
        return self._put(url, data, None, RequestsAuth(auth))

    def _put_with_auth_and_headers(self, url, data, auth, headers):
        return self._put(url, data, None, RequestsAuth(auth), headers)

    def _put_with_qiniu_mac_and_headers(self, url, data, auth, headers):
        return self._put(url, data, None, QiniuMacRequestsAuth(auth), headers)

    @return_wrapper
    async def _post_with_qiniu_mac(self, url, data, auth):
        qn_auth = QiniuMacRequestsAuth(
            auth) if auth is not None else None

        resp = await HTTPClient(request_class=CowClientRequest).post(
            url,
            json=data,
            auth=qn_auth,
            headers=self._headers
        )
        return resp

    @return_wrapper
    async def _get_with_qiniu_mac(self, url, params, auth):
        resp = await HTTPClient(request_class=CowClientRequest).get(
            url,
            params=params,
            auth=QiniuMacRequestsAuth(auth) if auth is not None else None,
            headers=self._headers)

        return resp

    @return_wrapper
    async def _get_with_qiniu_mac_and_headers(self, url, params, auth, headers):

        post_headers = self._headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        resp = await HTTPClient(request_class=CowClientRequest).get(
            url,
            params=params,
            auth=QiniuMacRequestsAuth(auth) if auth is not None else None,
            headers=post_headers)
        return resp

    @return_wrapper
    async def _delete_with_qiniu_mac(self, url, params, auth):

        resp = await HTTPClient(request_class=CowClientRequest).delete(
            url,
            params=params,
            auth=QiniuMacRequestsAuth(auth) if auth is not None else None,
            headers=self._headers)

        return resp

    @return_wrapper
    async def _delete_with_qiniu_mac_and_headers(self, url, params, auth, headers):
        post_headers = self._headers.copy()
        if headers is not None:
            for k, v in headers.items():
                post_headers.update({k: v})
        resp = await HTTPClient(request_class=CowClientRequest).delete(
            url,
            params=params,
            auth=QiniuMacRequestsAuth(auth) if auth is not None else None,
            headers=post_headers)

        return resp
    
    
class _TokenAuth:
    def __init__(self, token):
        self.token = token

    def __call__(self, r: CowClientRequest):
        r.headers['Authorization'] = 'UpToken {0}'.format(self.token)
        return r


class QiniuMacRequestsAuth(CowHttpAuthBase):

    def __call__(self, r: CowClientRequest):
        token = self.auth.token_of_request(
            r.method, r.headers.get('Host', None),
            r.url, self.auth.qiniu_headers(r.headers),
            r.headers.get('Content-Type', None),
            r.body
        )
        r.headers['Authorization'] = 'Qiniu {0}'.format(token)
        return r
    

class RequestsAuth(CowHttpAuthBase):

    def __call__(self, r: CowClientRequest):
        if r.body is not None and r.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
            token = self.auth.token_of_request(
                str(r.url), r.body, 'application/x-www-form-urlencoded')
        else:
            token = self.auth.token_of_request(str(r.url))
        r.headers['Authorization'] = 'QBox {0}'.format(token)
        return r

