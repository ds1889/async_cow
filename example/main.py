
import asyncio

from async_cow import AsyncCow


async def main():

    # 需要填写你的 Access Key 和 Secret Key
    access_key = ''
    secret_key = ''
    bucket_name = ''

    # 构建鉴权对象
    cow = AsyncCow(access_key, secret_key)

    b = cow.get_bucket(bucket_name)

    file_path = '/Users/admin/Desktop/README.md'

    with open(file_path, 'rb') as f:
        c = f.read()

    # 上传二进制流
    res = await b.put_data(
        key='AK47.jpg',
        data=c
    )
    for i in res:
        print(i)

    # 上传文件
    res = await b.put_file(
        key='AK472.jpg',
        file_path=file_path
    )
    for i in res:
        print(i)

    # 列出桶里的文件
    res = await b.list()
    for i in res:
        print(i)

if __name__ == '__main__':

    loop = asyncio.get_event_loop()

    loop.run_until_complete(main())




