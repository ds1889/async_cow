# -*- coding: utf-8 -*-
import os
import ssl
import json

import aiofiles
import aiohttp
import asyncio
import loguru

from aiohttp import ClientRequest

from enum import Enum

from async_cow.base import AsyncForSecond

logger = loguru.logger


class STATE(Enum):

    PENDING = 0x00
    FETCHING = 0x01
    SUCCESS = 0x02
    FAILURE = 0x03


DEFAULT_TIMEOUT = aiohttp.client.ClientTimeout(total=60, connect=10, sock_read=60, sock_connect=10)
DOWNLOAD_TIMEOUT = aiohttp.client.ClientTimeout(total=600, connect=10, sock_read=600, sock_connect=10)

CACERT_FILE = os.path.join(
    os.path.split(os.path.abspath(__file__))[0],
    r'../static/cacert.pem'
)


class _AsyncCirculator(AsyncForSecond):

    async def _sleep(self):

        await asyncio.sleep(self._current)


def _json_decoder(val, **kwargs):

    if isinstance(val, (str, type(None))):
        return json.loads(val, **kwargs)

    if isinstance(val, bytes):
        return json.loads(val.decode(r'utf-8'), **kwargs)

    else:
        raise TypeError(
            r'Expected str, bytes, or None; got %r' % type(val)
        )


class Result(dict):

    def __init__(self, status, headers, body, text, json_data):

        super().__init__(status=status, headers=headers, body=body, text=text, json=json_data)

    def __bool__(self):

        return (self.status >= 200) and (self.status <= 299)

    @property
    def status(self):

        return self.get(r'status')

    @property
    def status_code(self):

        return self.get(r'status')

    @property
    def headers(self):

        return self.get(r'headers')

    @property
    def body(self):

        return self.get(r'body')

    def text(self):
        return self.get(r'text')

    def json(self):
        return self.get(r'json')


class CowHttpAuthBase(object):

    def __init__(self, auth):
        self.auth = auth

    def __call__(self, r):

        raise NotImplementedError


class CowClientRequest(ClientRequest):

    def update_auth(self, auth: CowHttpAuthBase) -> None:

        if auth is None:
            auth = self.auth
        if auth is None:
            return

        auth(self)


class _HTTPClient:
    """HTTP客户端基类
    """

    def __init__(self, retry_count=5, timeout=None, **kwargs):

        global DEFAULT_TIMEOUT

        self._ssl_context = self._create_ssl_context()

        self._retry_count = retry_count

        self._session_config = kwargs
        self._session_config[r'timeout'] = timeout if timeout is not None else DEFAULT_TIMEOUT
        self._session_config.setdefault(r'raise_for_status', True)

    async def _handle_response(self, response):

        return await response.read()

    def _create_ssl_context(self):

        global CACERT_FILE

        return ssl.create_default_context(cafile=CACERT_FILE)

    def create_timeout(self, *, total=None, connect=None, sock_read=None, sock_connect=None):
        """生成超时配置对象

        Args:
            total: 总超时时间
            connect: 从连接池中等待获取连接的超时时间
            sock_read: Socket数据接收的超时时间
            sock_connect: Socket连接的超时时间

        """

        return aiohttp.client.ClientTimeout(
            total=total, connect=connect,
            sock_read=sock_read, sock_connect=sock_connect
        )

    async def send_request(self, method, url, data=None, params=None, cookies=None, headers=None, **settings) -> Result:

        response = None

        if headers is None:
            headers = {}

        if isinstance(data, dict):
            headers.setdefault(
                r'Content-Type',
                r'application/x-www-form-urlencoded'
            )

        settings[r'data'] = data
        settings[r'params'] = params
        settings[r'cookies'] = cookies
        settings[r'headers'] = headers

        logger.debug(
            r'{0} {1} => {2}'.format(
                method,
                url,
                str({key: val for key, val in settings.items() if isinstance(val, (str, list, dict))})
            )
        )

        settings.setdefault(r'ssl', self._ssl_context)

        async for times in _AsyncCirculator(max_times=self._retry_count):

            try:

                async with aiohttp.ClientSession(**self._session_config) as _session:

                    async with _session.request(method, url, **settings) as _response:

                        _json = None
                        try:
                            _json = await _response.json()
                        except:
                            pass
                        _text = ''
                        try:
                            _text = await _response.text()
                        except:
                            pass
                        response = Result(
                            _response.status,
                            dict(_response.headers),
                            await self._handle_response(_response),
                            _text,
                            _json,
                        )

            except aiohttp.ClientResponseError as err:

                # 重新尝试的话，会记录异常，否则会继续抛出异常

                if err.status < 500:
                    raise err
                elif times >= self._retry_count:
                    raise err
                else:
                    logger.warning(err)
                    continue

            except aiohttp.ClientError as err:

                if times >= self._retry_count:
                    raise err
                else:
                    logger.warning(err)
                    continue

            except Exception as err:

                raise err

            else:

                logger.info(f'{method} {url} => status:{response.status}')
                break

            finally:

                if times > 1:
                    logger.warning(f'{method} {url} => retry:{times}')

        return response


class _HTTPTextMixin:
    """Text模式混入类
    """

    async def _handle_response(self, response):

        return await response.text()


class _HTTPJsonMixin:
    """Json模式混入类
    """

    async def _handle_response(self, response):

        return await response.json(encoding=r'utf-8', loads=_json_decoder, content_type=None)


class _HTTPTouchMixin:
    """Touch模式混入类，不接收body数据
    """

    async def _handle_response(self, response):

        return dict(response.headers)


class HTTPClient(_HTTPClient):
    """HTTP客户端，普通模式
    """

    async def get(self, url, params=None, *, cookies=None, headers=None, **kwargs):
        """
        resp = await HTTPClient().get(...)
        usage: resp.body
        """
        resp = await self.send_request(aiohttp.hdrs.METH_GET, url, None, params, cookies=cookies, headers=headers, **kwargs)

        return resp

    async def options(self, url, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().options(...)
        resp.headers
        """
        resp = await self.send_request(aiohttp.hdrs.METH_OPTIONS, url, None, params, cookies=cookies, headers=headers, **kwargs)

        result = resp.headers

        return result

    async def head(self, url, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().head(...)
        resp.headers
        """
        resp = await self.send_request(aiohttp.hdrs.METH_HEAD, url, None, params, cookies=cookies, headers=headers, **kwargs)

        return resp

    async def post(self, url, data=None, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().post(...)
        resp.body
        """
        resp = await self.send_request(aiohttp.hdrs.METH_POST, url, data, params, cookies=cookies, headers=headers, **kwargs)

        return resp

    async def put(self, url, data=None, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().put(...)
        resp.body
        """
        resp = await self.send_request(aiohttp.hdrs.METH_PUT, url, data, params, cookies=cookies, headers=headers, **kwargs)

        return resp

    async def patch(self, url, data=None, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().patch(...)
        resp.body
        """
        resp = await self.send_request(aiohttp.hdrs.METH_PATCH, url, data, params, cookies=cookies, headers=headers, **kwargs)

        return resp

    async def delete(self, url, params=None, *, cookies=None, headers=None, **kwargs):
        """
        usage:
        resp = await HTTPClient().delete(...)
        resp.body
        """
        resp = await self.send_request(aiohttp.hdrs.METH_DELETE, url, None, params, cookies=cookies, headers=headers, **kwargs)

        return resp


class HTTPTextClient(_HTTPTextMixin, HTTPClient):
    """HTTP客户端，Text模式
    """
    pass


class HTTPJsonClient(_HTTPJsonMixin, HTTPClient):
    """HTTP客户端，Json模式
    """
    pass


class HTTPTouchClient(_HTTPTouchMixin, HTTPClient):
    """HTTP客户端，Touch模式
    """
    pass


class HTTPClientPool(HTTPClient):
    """HTTP带连接池客户端，普通模式
    """

    def __init__(self,
                 retry_count=5, use_dns_cache=True, ttl_dns_cache=10,
                 limit=100, limit_per_host=0, timeout=None,
                 **kwargs
                 ):

        super().__init__(retry_count, timeout, **kwargs)

        self._tcp_connector = aiohttp.TCPConnector(
            use_dns_cache=use_dns_cache,
            ttl_dns_cache=ttl_dns_cache,
            ssl=self._ssl_context,
            limit=limit,
            limit_per_host=limit_per_host,
        )

        self._session_config[r'connector'] = self._tcp_connector
        self._session_config[r'connector_owner'] = False

    async def close(self):

        if not self._tcp_connector.closed:
            await self._tcp_connector.close()


class HTTPTextClientPool(_HTTPTextMixin, HTTPClientPool):
    """HTTP带连接池客户端，Text模式
    """
    pass


class HTTPJsonClientPool(_HTTPJsonMixin, HTTPClientPool):
    """HTTP带连接池客户端，Json模式
    """
    pass


class HTTPTouchClientPool(_HTTPTouchMixin, HTTPClientPool):
    """HTTP带连接池客户端，Touch模式
    """
    pass


class Downloader(_HTTPClient):
    """HTTP文件下载器
    """

    def __init__(self, file, retry_count=5, timeout=None, **kwargs):

        global DOWNLOAD_TIMEOUT

        super().__init__(
            retry_count,
            timeout if timeout is not None else DOWNLOAD_TIMEOUT,
            **kwargs
        )

        self._file = file

        self._state = STATE.PENDING

        self._response = None

    @property
    def file(self):

        return self._file

    @property
    def state(self):

        return self._state

    @property
    def finished(self):

        return self._state in (STATE.SUCCESS, STATE.FAILURE)

    @property
    def response(self):

        return self._response

    async def _handle_response(self, response):

        if self._state != STATE.PENDING:
            return

        self._state = STATE.FETCHING
        self._response = response

        async with aiofiles.open(self._file, mode='wb') as stream:

            try:

                while True:

                    chunk = await response.content.read(65536)

                    if chunk:
                        stream.write(chunk)
                    else:
                        break

            except Exception as err:

                logger.error(err)

                self._state = STATE.FAILURE

            else:

                self._state = STATE.SUCCESS

        if self._state != STATE.SUCCESS and os.path.exists(self._file):
            os.remove(self._file)

    async def fetch(self, url, *, params=None, cookies=None, headers=None):

        result = False

        try:

            await self.send_request(aiohttp.hdrs.METH_GET, url, None, params, cookies=cookies, headers=headers)

            result = (self._state == STATE.SUCCESS)

        except Exception as err:

            logger.error(err)

            self._state = STATE.FAILURE

        return result


