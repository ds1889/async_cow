# Async Cow Python 七牛异步SDK

本SDK基于官方SDK改造而成，但又对其进行了进一步封装，简化了相关操作
例如：
- 1、不需要使用者关心token问题

- 2、简化了相关导包和引用，并且保持接口一致

- 3、实现了异步IO，引入协程概念，IO层面引入aiohttp，aiofiles等，使得本SDK适用于异步编程

  感谢您的星星❤

[官方SDK请见] https://developer.qiniu.com/kodo/1242/python

## 组织:

  QQ群: 614714752
  <img src='https://gitee.com/xixigroup/async_cow/raw/master/images/qq.jpeg' width='200'>

## Install

python解释器版本要求：> 3.6
```bash
# 标准安装
pip install async_cow

# 从官方源安装，你能获取最新版本SDK
pip install async_cow -i https://pypi.python.org/simple
```


## Usage

###初始化

在你需要的地方
```python
from async_cow import AsyncCow, ClientCow
cow = AsyncCow(<ACCESS_KEY>, <SECRET_KEY>)
client = ClientCow(<ACCESS_KEY>, <SECRET_KEY>)
```
###云存储桶操作

```python
b = cow.get_bucket(<BUCKET>)
```

后面都用这个桶对象来操作。 它代表了`<BUCKET>`

#### 列出所有的bucket
```python
res = await b.buckets()
```

#### 列出一个bucket中的所有文件
```python
res = await b.list()
```
这个方法还有 marker, limit, prefix这三个可选参数，详情参考官方文档

bucket相关方法和用法和官方SDK同步

#### 上传

```python
file_path = '/Users/admin/Desktop/123.jpg'

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


#### 拷贝，移动（改名）经测试，只能在桶内copy和move

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

###短信客户端操作

```python
# 获取一个短信客户端对象
sms = cow.get_sms()
```

#### 创建，查看，编辑，删除签名

```python
await sms.createSignature(<signature>, <source>)
await sms.querySignature()
await sms.updateSignature(<id>, <signature>)
await sms.deleteSignature(<id>)
```

#### 创建，查看，编辑，删除模版

```python
await sms.createTemplate(<name>, <template>, <type>, <description>, <signature_id>)
await sms.queryTemplate(<audit_status>)
await sms.updateTemplate(<id>, <name>, <template>, <description>, <signature_id>)
await sms.deleteTemplate(<id>)
```

####发送短信，查看发送记录，查询发送计费条数

```python
await sms.sendMessage(<template_id>, <mobiles>, <parameters>)
await sms.get_messages_info()
await sms.get_charge_message_count(<start>, <end>, <g>, <status>)
```

### 持久化

```python
# 获取持久化类对象
p = cow.get_persistent_fop(<bucket>)
```

#### 文件持久化

```python
await p.execute(<key>, <fops>)
```



###直播连麦管理

```python
# 获取一个管理类对象
r = cow.get_rtc_server()
```

#### 创建，获取，修改，删除app

```python
await r.create_app(<data>)
await r.get_app()
await r.update_app(<app_id>, <data>)
await r.delete_app(<app_id>)
```

#### 用户列表，踢出用户

```python
await r.list_user(<app_id>, <data>)
await r.kick_user(<app_id>, <data>, <user_id>)
```

#### 查看活跃房间

```python
await r.list_active_rooms(<app_id>)
```



### CDN管理

```python
# 获取cdn管理类对象
cdn = cow.get_cdn_manager()
```

#### 刷新文件、目录

```python
await cdn.refresh_urls(<urls>)
await cdn.refresh_dirs(<dirs>)
# 同时刷新urls和dirs
await cdn.refresh_urls_and_dirs(<urls>, <dirs>)
```

#### 预取文件列表

```python
await cdn.prefetch_urls(<urls>)
```

#### 查询宽带、流量数据

```python
# 宽带
await cdn.get_bandwidth_data(<domains>, <start_date>, <end_date>, <granularity>)
# 流量
await cdn.get_flux_data(<domains>, <start_date>, <end_date>, <granularity>)
```

#### 获取日志下载链接

```python
await cdn.get_log_list_data(<domains>, <log_date>)
```

#### 修改证书

```python
await cdn.put_httpsconf(<name>, <certid>)
```



### 域名管理

```python
# 获取域名管理类对象
d = cow.get_domain_manager()
```

#### 创建，查看，删除域名

```python
await d.create_domain(<name>, <body>)
await d.get_domain(<name>)
await d.delete_domain(<name>)
```

#### 上线、下线域名

```python
await d.domain_online(<name>)
await d.domain_offline(<name>)
```

#### 创建、修改证书

```python
await d.create_sslcert(<name>, <certid>, <forceHttps>)
await d.put_httpsconf(<name>, <common_name>, <pri>, <ca>)
```



### 账号客户端

```python
# 获取帐号客户端对象
app = client.get_app()
```

#### 创建、获取管理客户端

```python
await app.create_qcos_client(<app_uri>)
await app.get_qcos_client(<app_uri>)
```

#### 账号密钥

```python
# 获取帐号下应用的密钥
await app.get_app_keys(<app_uri>)
# 获取帐号下可用的应用的密钥
await app.get_valid_app_auth(<app_uri>)
```

#### 当前账号的信息

```python
await app.get_account_info()
```

####获得指定应用所在区域的产品信息

```python
await app.get_app_region_products(<app_uri>)
```

#### 获取指定区域产品信息

```python
await app.get_region_products(<region>)
```

#### 获得账号可见的区域的信息

```python
await app.list_regions()
```

#### 创建、获得、删除当前账号的应用

```python
await app.create_app(<args>)
await app.list_apps()
await app.delete_app(<app_uri>)
```

### 资源管理客户端

```python
# 获取资源管理客户端对象
q = client.get_qcos_client()
```

####创建、获取、删除服务组

```python
await q.create_stack(<args>)
await q.get_stack(<stack>)
await q.delete_stack(<stack>)
```

#### 启动、停止服务组

```python
await q.start_stack(<stack>)
await q.stop_stack(<stack>)
```

#### 创建、获取、更新删除服务

```python
await q.create_service(<stack>, <args>)
# 查看服务
await q.get_service_inspect(<stack>, <service>)
# 获得服务列表
await q.list_services(<stack>)
await q.update_service(<stack>, <service>, <args>)
await q.delete_service(<stack>, <service>)
```

#### 启动、停止服务

```python
await q.start_service(<stack>, <service>)
await q.stop_service(<stack>, <service>)
```

#### 扩容、缩容服务

```python
await q.scale_service(<stack>, <service>, <args>)
```

#### 创建、删除、扩容存储卷

```python
await q.create_service_volume(<stack>, <service>, <args>)
await q.delete_service_volume(<stack>, <service>, <volume>)
await q.extend_service_volume(<stack>, <service>, <volume>, <args>)
```

#### 查看、列出容器

```python
await q.get_container_inspect(<ip>)
await q.list_containers()
```

#### 启动、停止、重启容器

```python
await q.start_container(<ip>)
await q.stop_container(<ip>)
await q.restart_container(<ip>)
```

#### 接入点

```python
# 列出接入点
await q.list_aps()
# 搜索接入点
await q.search_ap(<mode>, <query>)
# 查看接入点
await q.get_ap(<apid>)
# 申请接入点
await q.create_ap(<args>)
# 更新接入点
await q.update_ap(<apid>, <args>)
# 更新接入点端口配置
await q.set_ap_port(<apid>, <port>, <args>)
# 释放接入点
await q.delete_ap(<apid>)
```

#### 自定义域名

```python
# 绑定自定义域名
await q.publish_ap(<apid>, <args>)
# 解绑自定义域名
await q.unpublish_ap(<apid>, <args>)
```

#### 查看健康检查结果

```python
await q.get_ap_port_healthcheck(<apid>, <port>)
```

#### 调整后端实例配置

```python
await q.set_ap_port_container(<apid>, <port>, <args>)
```

#### 接入点端口

```python
# 临时关闭接入点端口
await q.disable_ap_port(<apid>, <port>)
# 开启接入点端口
await q.enable_ap_port(<apid>, <port>)
```

#### 列出入口提供商

```python
await q.get_ap_providers()
```

#### 获取一次性代理地址

```python
await q.get_web_proxy(<backend>)
```





## 测试

###桶测试

1.  首先从github clone项目到本地
2.  在项目中有example供测试，配置好main.py中的access_key、secret_key、bucket以及file_path参数后即可开始测试

特别鸣谢：[Hagworm](https://gitee.com/wsb310/hagworm) 以及七牛官方

欢迎大佬指正！感谢您的星星❤