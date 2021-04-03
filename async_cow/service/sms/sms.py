# -*- coding: utf-8 -*-

import json


class Sms:
    """
    TODO 所有功能方法都将返回协程对象，必须用await调用，和原七牛SDK保持接口同步
    文档：https://developer.qiniu.com/sms/5812/sms-product-introduction
    Attributes:
        cow: AsyncCow对象
        不希望你直接调用本类
        而是通过下列方式调用

        sms = AsyncCow(<access_key>, <secret_key>).get_sms()
        sig_dic = await sms.createSignature(<signature>, <source>, <pics>)
    """

    def __init__(self, cow):
        self.cow = cow
        self.server = 'https://sms.qiniuapi.com'

    def createSignature(self, signature, source, pics=None):
        """
        *创建签名
        *signature: string类型，必填，【长度限制8个字符内】超过长度会报错
        *source: string类型，必填，申请签名时必须指定签名来源。取值范围为：
            enterprises_and_institutions 企事业单位的全称或简称
            website 工信部备案网站的全称或简称
            app APP应用的全称或简称
            public_number_or_small_program 公众号或小程序的全称或简称
            store_name 电商平台店铺名的全称或简称
            trade_name 商标名的全称或简称
        *pics: 签名对应的资质证明图片进行 base64 编码格式转换后的字符串
        * @ return: 类型array
        {
            "signature_id": < signature_id >
        }
        """
        req = {}
        req['signature'] = signature
        req['source'] = source
        if pics:
            req['pics'] = pics
        body = json.dumps(req)
        url = '{0}/v1/signature'.format(self.server)
        return self._post(url, body)

    def querySignature(self, audit_status=None, page=1, page_size=20):
        """
        查询签名
        * audit_status: 审核状态 string 类型，可选，取值范围为: "passed"(通过), "rejected"(未通过), "reviewing"(审核中)
        * page:页码 int  类型，
        * page_size: 分页大小 int 类型，可选， 默认为20
        *@return: 类型array {
            "items": [{
            "id": string,
            "signature": string,
            "source": string,
            "audit_status": string,
            "reject_reason": string,
            "created_at": int64,
            "updated_at": int64
                }...],
            "total": int,
            "page": int,
            "page_size": int,
            }
        """
        url = '{0}/v1/signature'.format(self.server)
        if audit_status:
            url = '{0}?audit_status={1}&page={2}&page_size={3}'.format(url, audit_status, page, page_size)
        else:
            url = '{0}?page={1}&page_size={2}'.format(url, page, page_size)
        return self._get(url)

    def updateSignature(self, id, signature):
        """
        编辑签名
        *  id 签名id : string 类型，必填，
        * signature: string 类型，必填，
        request 类型array {
        "signature": string
        }
        :return:
        """
        url = '{0}/v1/signature/{1}'.format(self.server, id)
        req = {}
        req['signature'] = signature
        body = json.dumps(req)
        return self._put(url, body)

    def deleteSignature(self, id):

        """
        删除辑签名
        *  id 签名id : string 类型，必填，
        * @retrun : 请求成功 HTTP 状态码为 200

        """
        url = '{0}/v1/signature/{1}'.format(self.server, id)
        return self._delete(url)

    def createTemplate(self, name, template, type, description, signature_id):
        """
        创建模版
        :param name: 模板名称 string 类型 ，必填
        :param template: 模板内容 string  类型，必填
        :param type: 模板类型 string 类型，必填，
                    取值范围为: notification (通知类短信), verification (验证码短信), marketing (营销类短信)
        :param description: 申请理由简述 string  类型，必填
        :param signature_id: 已经审核通过的签名 string  类型，必填
        :return: 类型 array {
        "template_id": string
                }
        """
        url = '{0}/v1/template'.format(self.server)
        req = {}
        req['name'] = name
        req['template'] = template
        req['type'] = type
        req['description'] = description
        req['signature_id'] = signature_id
        body = json.dumps(req)
        return self._post(url, body)

    def queryTemplate(self, audit_status, page=1, page_size=20):
        """
        查询模版
        :param audit_status: 审核状态, 取值范围为: passed (通过), rejected (未通过), reviewing (审核中)
        :param page: 页码。默认为 1
        :param page_size: 分页大小。默认为 20
        :return:{
        "items": [{
            "id": string,
            "name": string,
            "template": string,
            "audit_status": string,
            "reject_reason": string,
            "type": string,
            "signature_id": string, // 模版绑定的签名ID
            "signature_text": string, // 模版绑定的签名内容
            "created_at": int64,
            "updated_at": int64
            }...],
            "total": int,
            "page": int,
            "page_size": int
        }
        """
        url = '{0}/v1/template'.format(self.server)
        if audit_status:
            url = '{0}?audit_status={1}&page={2}&page_size={3}'.format(url, audit_status, page, page_size)
        else:
            url = '{0}?page={1}&page_size={2}'.format(url, page, page_size)
        return self._get(url)

    def updateTemplate(self, id, name, template, description, signature_id):
        """
        更新模版
        :param id: template_id
        :param name: 模板名称 string 类型 ，必填
        :param template: 模板内容 string  类型，必填
        :param description: 申请理由简述 string  类型，必填
        :param signature_id: 已经审核通过的签名 string  类型，必填
        :return: 请求成功 HTTP 状态码为 200
        """
        url = '{0}/v1/template/{1}'.format(self.server, id)
        req = {}
        req['name'] = name
        req['template'] = template
        req['description'] = description
        req['signature_id'] = signature_id
        body = json.dumps(req)
        return self._put(url, body)

    def deleteTemplate(self, id):
        """
        删除模版
        :param id: template_id
        :return: 请求成功 HTTP 状态码为 200
        """
        url = '{0}/v1/template/{1}'.format(self.server, id)
        return self._delete(url)

    def sendMessage(self, template_id, mobiles, parameters):
        """
        发送短信
        :param template_id:  模板 ID
        :param mobiles: 手机号
        :param parameters: 自定义魔法变量，变量设置在创建模板时，参数template指定
        :return:{
            "job_id": string
        }
        短信发送给用户后，将会通过回调业务 URL 的方式，通知业务方用户发送短信的状态。
        回调文档见：https://developer.qiniu.com/sms/5910/message-push

        """
        url = '{0}/v1/message'.format(self.server)
        req = {}
        req['template_id'] = template_id
        req['mobiles'] = mobiles
        req['parameters'] = parameters
        body = json.dumps(req)
        return self._post(url, body)

    def get_charge_message_count(self, start, end, g, status):
        """
        查询发送计费条数
        https://developer.qiniu.com/sms/7926/query-send-billing-number
        名称	必填	描述
        start	是	查询开始时间。格式：2006-01-02
        end	是	查询结束时间。格式：2006-01-02
        g	是	计量数据聚合粒度，支持： day, 5min
        status	是	短信的状态，支持：“success”(发送成功), “failed”(发送失败), “sending”(发送中)
        :return  通知短信和验证码短信会统一到 系统短信 计量计费
        {
            "data": {
                "marketing": { // 营销短信统计
                    "times": [
                        1609430400,
                    ],
                    "values": [
                        0,
                    ]
                },
                "notification": { // 通知短信统计
                    "times": [
                        1609430400,
                    ],
                    "values": [
                        0,
                    ]
                },
                "verification": {// 验证码短信统计
                    "times": [
                        1609430400,
                    ],
                    "values": [
                        0,
                    ]
                },
                "voice": { // 语音短信统计
                    "times": [
                        1609430400,
                    ],
                    "values": [
                        0,
                    ]
                }
            }
        }

        """

        url = f'/v1/user/statistics?start={start}&end={end}&g={g}&status={status}'

        return self._get(url)

    def get_messages_info(self,
                          job_id=None,
                          message_id=None,
                          mobile=None,
                          status=None,
                          template_id=None,
                          type=None,
                          start=None,
                          end=None,
                          page=1,
                          page_size=20,
                          ):
        """
        查询发送记录，文档：https://developer.qiniu.com/sms/api/5852/query-send-sms

        名称	必填	描述
        job_id	否	发送任务返回的 id
        message_id	否	单条短信发送接口返回的 id
        mobile	否	接收短信的手机号码
        status	否	短信的状态，sending: 发送中，success: 发送成功，failed: 发送失败，waiting: 等待发送
        template_id	否	模版 id
        type	否	短信类型，marketing: 营销短信，notification: 通知短信，verification: 验证码类短信，voice: 语音短信
        start	否	开始时间，timestamp，例如: 1563280448
        end	否	结束时间，timestamp，例如: 1563280471
        page	否	页码，默认为 1
        page_size	否	每页返回的数据条数，默认20，最大200

        :return:
        {
            "page": int,
            "page_size": int,
            "items":[{
                "message_id": string,
                "job_id": string,
                "mobile": string,
                "content": string,
                "status": string,
                "type": string,
                "error": string, // 短信发送失败详细状态信息
                "count": int, // 发送的短信条数
                "created_at": timestamp,  // 短信发送时间
                "delivrd_at": timestamp // 如果短信发送失败，那么不会返回这个字段
            }...]
        }
        """
        params = {
            'page': page,
            'page_size': page_size,
        }
        if job_id is not None:
            params['job_id'] = job_id
        if message_id is not None:
            params['message_id'] = message_id
        if mobile is not None:
            params['mobile'] = mobile
        if status is not None:
            params['status'] = status
        if template_id is not None:
            params['template_id'] = template_id
        if type is not None:
            params['type'] = type
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        
        url = "{0}/v1/messages".format(self.server)
        return self._get(url, params=params)

    def _post(self, url, data=None):
        headers = {'Content-Type': 'application/json'}
        return self.cow.http._post_with_qiniu_mac_and_headers(url, data, self.cow.auth, headers)

    def _get(self, url, params=None):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.cow.http._get_with_qiniu_mac_and_headers(url, params, self.cow.auth, headers)

    def _put(self, url, data=None):
        headers = {'Content-Type': 'application/json'}
        return self.cow.http._put_with_qiniu_mac_and_headers(url, data, self.cow.auth, headers)

    def _delete(self, url, data=None):
        headers = {'Content-Type': 'application/json'}
        return self.cow.http._delete_with_qiniu_mac_and_headers(url, data, self.cow.auth, headers)
