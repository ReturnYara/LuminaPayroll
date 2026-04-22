import requests
from typing import Dict, List, Optional
import logging

class QueryPayDetailsApi:
    """查询发放单详情接口封装"""

    def __init__(self):
        self.base_url = "https://c4.yonyoucloud.com"
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def query_pay_details(self, pay_file_id: str) -> Dict:
        """查询发放单详情"""
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/queryPayDetails"
        params = {
            "payfileId": pay_file_id
        }
        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        return response.json()