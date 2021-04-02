# -*- coding: utf-8 -*-

import setuptools

from async_cow import __version__


with open(r'./README.md', r'r', encoding=r'utf8') as stream:
    long_description = stream.read()

setuptools.setup(
    name=r'async_cow',
    version=__version__,
    license=r'Apache License Version 2.0',
    platforms=[r'all'],
    author=r'Xixi.Dong',
    author_email=r'xq1889@163.com',
    description=r'Network Development Suite',
    long_description=long_description,
    long_description_content_type=r'text/markdown',
    url=r'https://gitee.com/xixigroup/wintersweet',
    packages=setuptools.find_packages(),
    python_requires=r'>= 3.6',
    install_requires=[
        'aiofiles==0.6.0',
        'aiohttp==3.7.4',
        'async-timeout==3.0.1',
        'qiniu==7.3.1',
        'urllib3==1.26.2',
        'loguru==0.5.3',
        'cachetools==4.2.1'
    ],
    classifiers=[
        r'Programming Language :: Python :: 3.7',
        r'License :: OSI Approved :: Apache Software License',
        r'Operating System :: POSIX :: Linux',
    ],
    include_package_data=True
)
