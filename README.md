# Async Cow Python 七牛异步SDK

本SDK基于官方SDK改造而成，但又对其进行了进一步封装，简化了相关操作
例如：
- 1、不需要使用者关心token问题
- 2、简化了相关导包和引用，并且保持接口一致
- 3、实现了异步IO，引入协程概念，IO层面引入aiohttp，aiofiles等，使得本SDK适用于异步编程

官方SDK请见 
[![官方SDK](http://qiniutek.com/images/logo-2.png)](https://github.com/qiniu/python-sdk)

## Install

```bash
pip install async_cow
```


## Usage

#### 初始化

在你需要的地方
```python
from async_cow import AsyncCow
cow = AsyncCow(<ACCESS_KEY>, <SECRET_KEY>)
```

然后就可以通过 `cow.stat(<BUCKET>, <FILENAME>)` 这样来进行操作.
但为了简化操作，并且考虑到大多数都是在一个bucket中进行文件操作，
所以建议再做一步：

```python
b = cow.get_bucket(<BUCKET>)
```

后面都用这个`b`对象来操作。 它代表了`<BUCKET>`

#### 列出所有的bucket
```python
res = await cow.buckets()
```

#### 列出一个bucket中的所有文件
```python
res = await b.list()
```
这个方法还有 marker, limit, prefix这三个可选参数，详情参考官方文档

bucket相关方法和用法和官方SDK同步

#### 上传

```python
file_path = '/Users/admin/Desktop/per_project/async_cow/README.md'

with open(file_path, 'rb') as f:
    c = f.read()

# 上传二进制流
res = await b.put_data(
    key='AK47.jpg',  # 上传后的文件名
    data=c
)

# 上传文件
res = await b.put_file(
    key='AK472.jpg',  # 上传后的文件名
    file_path=file_path
)
for i in res:
    print(i)

```


#### 删除，查看文件信息
```python
await b.stat('a')                 # 查看单个文件信息
await b.delete('a')               # 删除单个文件
```


#### 拷贝，移动（改名）

这两个操作需要提供源文件名和目标文件名

```python
await b.copy('a', 'b')                            # 将'a' 拷贝至'b'
await b.move('a', 'b')                            # 将'a' 改名为'b'
```

有没有觉得比官方SDK容易使用多呢？

--------

#### 异常

在封装aiohttp操作时已经处理了大部分异常和重试过程，但仍会存在一些意外

所以安全的做法是这样：

```python
try:
    await b.delete('a')
except Exception as e:
    # 自行处理
    pass
```


## 测试

1.  首先从github clone项目到本地
2.  在项目中有example供测试，配置好main.py中的access_key、secret_key、bucket以及file_path参数后即可开始测试


特别鸣谢：[seven-cow](https://github.com/yueyoum/seven-cow)，[Hagworm](https://gitee.com/wsb310/hagworm) 以及七牛官方

欢迎大佬指正！感谢您的星星❤