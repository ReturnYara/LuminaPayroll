import requests
from typing import Dict, List, Optional
import logging


class QueryPayDetailsApi:
    """查询发放单详情接口封装"""

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com", session: requests.Session = None):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json;charset=UTF-8",
            "origin": base_url,
            "referer": f"{base_url}/",
            "domain-key": "yonbip-hr-paybiz"
        }

    def set_xsrf_token(self, token: str):
        """设置 XSRF Token"""
        self.headers["x-xsrf-token"] = token

    def query_pay_details(self, data: dict) -> requests.Response:
        """
        查询发放单详情（POST）

        :param data: 完整请求参数字典，包含 billnum, ownDomain, serviceCode,
                     payfileId, queryIdStr, onlyNoBank, page 等字段
        """
        service_code = data.get("serviceCode", "HRXZHS_MDD_030030")
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/queryPayDetails?serviceCode={service_code}"

        payload = {
            "billnum": data.get("billnum", "wa_pay_file_doc_list"),
            "ownDomain": data.get("ownDomain", "yonbip-hr-paybiz"),
            "serviceCode": service_code,
            "payfileId": data["payfileId"],
            "queryIdStr": data["queryIdStr"],
            "onlyNoBank": data.get("onlyNoBank", False),
            "page": data.get("page", {"pageSize": 200, "pageIndex": 1, "recordCount": 2}),
        }

        self.logger.info(f"[queryPayDetails] payfileId={payload['payfileId']}")
        response = self.session.post(url, json=payload, headers=self.headers, verify=False)
        self.logger.info(f"[queryPayDetails] status={response.status_code}")
        return response
