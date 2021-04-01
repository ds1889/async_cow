# -*- coding: utf-8 -*-

"""
pythoncompat
"""
import io
import sys
import json

from urllib.parse import urlparse

StringIO = io.StringIO
BytesIO = io.BytesIO

builtin_str = str
str = str
bytes = bytes
basestring = (str, bytes)
numeric_types = (int, float)


def b(data):
    if isinstance(data, str):
        return data.encode('utf-8')
    return data


def s(data):
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return data


def u(data):
    return data
