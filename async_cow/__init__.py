

version_info = (0, 4, 0)
VERSION = __version__ = '.'.join(map(str, version_info))

"""
from async_cow.cow import AsyncCow

Usage:
cow = AsyncCow(ACCESS_KEY, SECRET_KEY)
b = cow.get_bucket(BUCKET)
await b.put_file('a', path)
await b.stat('a')
await b.delete('a')
await b.copy('a', 'c')
await b.move('a', 'c')
"""

from async_cow.cow import AsyncCow, ClientCow

