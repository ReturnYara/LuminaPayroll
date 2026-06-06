"""发放单（新建、保存、计算）API 封装

封装发放单的创建和计算接口，用于预置步骤6。

核心流程：
- 查询是否已有发放单
- 新建发放单并保存
- 触发计算并等待完成
"""

import json
import time
import requests
import logging
from typing import Dict, List, Optional, Any


class PayDocApi:
    """发放单创建与计算接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_030030"

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com",
                 session: requests.Session = None,
                 org_id: str = "666666"):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.org_id = org_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json;charset=UTF-8",
            "origin": base_url,
            "referer": f"{base_url}/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/146.0.0.0 Safari/537.36",
            "domain-key": "yonbip-hr-paybiz"
        }

    def set_xsrf_token(self, token: str):
        """设置 XSRF Token"""
        self.headers["x-xsrf-token"] = token

    # ==================== 查询接口 ====================

    def list_pay_docs(self, page_index: int = 1, page_size: int = 20,
                      name: str = None, period: str = None) -> Dict[str, Any]:
        """查询发放单列表

        Args:
            page_index: 页码
            page_size: 每页条数
            name: 发放单名称过滤
            period: 所属期过滤

        Returns:
            响应 data
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "terminalType": "1"
        }

        common_vos = [
            {"value1": self.org_id, "itemName": "busiOrgName"},
        ]
        if name:
            common_vos.append({"value1": name, "itemName": "name"})
        if period:
            common_vos.append({"value1": period, "itemName": "period"})

        payload = {
            "page": {
                "pageSize": page_size,
                "pageIndex": page_index
            },
            "billnum": "wa_pay_file",
            "condition": {
                "commonVOs": common_vos
            },
            "bClick": True,
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "ownDomain": "yonbip-hr-paybiz"
        }

        self.logger.info(f"[list_pay_docs] name={name}, period={period}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询发放单失败: {result.get('message', '')}")

        return result["data"]

    def pay_doc_exists(self, name: str) -> Optional[Dict]:
        """检查指定名称的发放单是否已存在"""
        data = self.list_pay_docs(page_index=1, page_size=1, name=name)
        record_list = data.get("recordList", [])
        if record_list:
            self.logger.info(f"[pay_doc_exists] 发放单已存在: {name}, id={record_list[0].get('id')}")
            return record_list[0]
        return None

    # ==================== 创建接口 ====================

    def create_pay_doc(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """新建并保存发放单

        Args:
            doc_data: 发放单数据，包含名称、方案、期间等

        Returns:
            创建结果，包含发放单ID
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/save"
        params = {
            "cmdname": "cmdSave",
            "businessActName": "新建发放单-保存",
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "sbillno": "wa_pay_file",
            "orgId": self.org_id
        }

        payload = {
            "billnum": "wa_pay_file_add_card",
            "data": json.dumps(doc_data, ensure_ascii=False)
        }

        self.logger.info(f"[create_pay_doc] 创建发放单")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"创建发放单失败: {result.get('message', '')}")

        pay_file_id = result["data"].get("id", "")
        self.logger.info(f"[create_pay_doc] 创建成功, payFileId={pay_file_id}")
        return result["data"]

    # ==================== 计算接口 ====================

    def verify_calculate(self, pay_file_id: str) -> Dict[str, Any]:
        """验证计算条件

        Args:
            pay_file_id: 发放单ID

        Returns:
            验证结果
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/verifyCalculate"
        params = {"serviceCode": self.SERVICE_CODE}
        payload = {
            "payFileId": pay_file_id,
            "selectRowDocIds": []
        }

        self.logger.info(f"[verify_calculate] payFileId={pay_file_id}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"验证计算条件失败: {result.get('message', '')}")

        return result["data"]

    def calculate(self, pay_file_id: str, query_id_str: str) -> Dict[str, Any]:
        """执行计算

        Args:
            pay_file_id: 发放单ID
            query_id_str: 查询标识串

        Returns:
            计算结果
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/calcalutePayDocDatas"
        params = {"serviceCode": self.SERVICE_CODE}
        payload = {
            "selectRowDocIds": [],
            "calcaluteType": 0,
            "pageNum": 1,
            "pageSize": 999999,
            "itemReq": [],
            "billnum": "wa_pay_file_doc_list",
            "ownDomain": "yonbip-hr-paybiz",
            "serviceCode": self.SERVICE_CODE,
            "payfileId": pay_file_id,
            "queryIdStr": query_id_str,
            "onlyNoBank": False,
            "page": {
                "pageSize": 200,
                "pageIndex": 1,
                "recordCount": 0
            }
        }

        self.logger.info(f"[calculate] payFileId={pay_file_id}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"执行计算失败: {result.get('message', '')}")

        return result["data"]

    def get_progress(self, pay_file_id: str) -> int:
        """获取计算进度百分比

        Returns:
            0-100 的进度值
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/getCalProgressPercent"
        params = {
            "payfileId": pay_file_id,
            "serviceCode": self.SERVICE_CODE
        }

        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            return 0

        return result["data"].get("percentage", 0)

    def wait_calculate_complete(self, pay_file_id: str, timeout: int = 120,
                                interval: int = 2) -> bool:
        """等待计算完成

        Args:
            pay_file_id: 发放单ID
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）

        Returns:
            True=计算完成, False=超时
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            progress = self.get_progress(pay_file_id)
            self.logger.info(f"[wait_calculate] progress={progress}%")

            if progress >= 100:
                return True

            time.sleep(interval)

        self.logger.error("[wait_calculate] 计算超时")
        return False
