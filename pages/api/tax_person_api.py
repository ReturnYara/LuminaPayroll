"""纳税人员同步 API 封装

封装纳税人员的查询和同步接口，用于预置步骤4。

核心发现（从 HAR 确认）：
- "创建纳税人员" = 调用 syncReportPerson（GET 请求）
- 将发薪人员同步到税务模块，同步操作，无需轮询
- serviceCode: HRXZHS_MDD_040005
- orgId 使用的是 taxOrg 的 id（不是业务组织 id）

核心接口：
- bill/ref/getRefData (waTaxOrg_ref): 获取税务组织
- bill/list (billnum=tax_payer_list): 查询已有纳税人员
- taxPayer/syncReportPerson: 同步发薪人员到税务模块（GET）
"""

import json
import requests
import logging
from typing import Dict, List, Optional, Any


class TaxPersonApi:
    """纳税人员同步接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_040005"
    BILLNUM_LIST = "tax_payer_list"
    SBILLNO = "psn_report_tabgroup"

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com",
                 session: requests.Session = None,
                 org_id: str = "666666"):
        """
        Args:
            base_url: 环境 URL
            session: 认证 Session
            org_id: 业务组织 ID（注意：sync 用的是 taxOrgId，不是这个）
        """
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

    # ==================== 参照查询 ====================

    def get_tax_org(self) -> List[Dict]:
        """获取税务组织参照

        Returns:
            税务组织列表，每条记录包含:
            - id: taxOrgId（用于 sync 和 list 的 orgId 参数）
            - taxName: 税务组织名称
            - taxMemberNumber: 纳税人识别号
            - belongOrg: 所属业务组织 ID
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/ref/getRefData"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "refCode": "waTaxOrg_ref",
            "sourceBillnum": self.BILLNUM_LIST,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO
        }

        payload = {
            "page": {"pageSize": 50, "pageIndex": 1},
            "refCode": "waTaxOrg_ref",
            "billnum": "tax_payer_card",
            "serviceCode": self.SERVICE_CODE,
            "condition": {
                "commonVOs": [
                    {"itemName": "schemeName", "value1": "默认方案"},
                    {"itemName": "isDefault", "value1": True}
                ],
                "isExtend": True,
                "simpleVOs": [
                    {"field": "enable", "op": "eq", "value1": 1},
                    {"field": "serviceCode", "op": "eq", "value1": self.SERVICE_CODE}
                ]
            },
            "dataType": "grid"
        }

        self.logger.info("[get_tax_org] 查询税务组织")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询税务组织失败: {result.get('message', '')}")

        records = result["data"].get("recordList", [])
        self.logger.info(f"[get_tax_org] 找到 {len(records)} 个税务组织")
        return records

    # ==================== 查询接口 ====================

    def list_persons(self, tax_org_id: str, page_index: int = 1,
                     page_size: int = 20,
                     effective_date_start: str = "2025-01-01",
                     effective_date_end: str = "2025-01-31") -> Dict[str, Any]:
        """查询已有纳税人员列表

        Args:
            tax_org_id: 税务组织ID（从 get_tax_org 获取的 id 字段）
            page_index: 页码
            page_size: 每页条数
            effective_date_start: 生效日期起始
            effective_date_end: 生效日期截止

        Returns:
            响应 data（包含 recordCount, recordList）
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "sbillno": self.SBILLNO,
            "terminalType": "1"
        }

        payload = {
            "page": {
                "pageSize": page_size,
                "pageIndex": page_index
            },
            "billnum": self.BILLNUM_LIST,
            "condition": {
                "commonVOs": [
                    {"itemName": "schemeName", "value1": "默认方案"},
                    {"itemName": "isDefault", "value1": True},
                    {"value1": [tax_org_id], "itemName": "orgId"},
                    {"value1": effective_date_start, "value2": effective_date_end,
                     "itemName": "effectiveDate"}
                ],
                "isExtend": True,
                "simpleVOs": [
                    {"op": "eq", "field": "dr", "value1": "0"}
                ]
            },
            "bClick": True,
            "bEmptyWithoutFilterTree": False,
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "sbillno": self.SBILLNO,
            "ownDomain": "yonbip-hr-paybiz"
        }

        self.logger.info(f"[list_persons] taxOrgId={tax_org_id}, page={page_index}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询纳税人员失败: {result.get('message', '')}")

        return result["data"]

    def has_persons(self, tax_org_id: str) -> bool:
        """检查是否已有纳税人员

        Args:
            tax_org_id: 税务组织ID

        Returns:
            True=已有人员, False=无人员
        """
        data = self.list_persons(tax_org_id, page_index=1, page_size=1)
        records = data.get("recordList", [])
        has = len(records) > 0
        self.logger.info(f"[has_persons] taxOrgId={tax_org_id}, has={has}")
        return has

    # ==================== 同步接口 ====================

    def sync_report_person(self, tax_org_id: str) -> bool:
        """同步发薪人员到税务模块

        这是一个 GET 请求，同步操作，无需轮询。
        将已匹配的发薪人员同步为纳税人员。

        Args:
            tax_org_id: 税务组织ID（注意：不是业务组织ID）

        Returns:
            True=同步成功
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/taxPayer/syncReportPerson"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO,
            "orgId": tax_org_id
        }

        self.logger.info(f"[sync_report_person] taxOrgId={tax_org_id}")
        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"同步纳税人员失败: {result.get('message', '')}")

        self.logger.info("[sync_report_person] 同步成功")
        return True

    # ==================== 完整流程封装 ====================

    def sync_persons(self, tax_org_id: str = None) -> Dict[str, Any]:
        """完整的纳税人员同步流程

        1. 获取税务组织（如未指定）
        2. 检查是否已有人员（幂等）
        3. 执行同步
        4. 验证同步结果

        Args:
            tax_org_id: 税务组织ID，为 None 则自动查询

        Returns:
            {"action": "synced"|"skipped", "tax_org_id": ..., "person_count": ...}
        """
        # 1. 获取税务组织
        if not tax_org_id:
            tax_orgs = self.get_tax_org()
            if not tax_orgs:
                raise RuntimeError("未找到税务组织")
            tax_org_id = tax_orgs[0]["id"]
            self.logger.info(f"[sync_persons] 使用税务组织: id={tax_org_id}, "
                             f"name={tax_orgs[0].get('taxName', '')}")

        # 2. 幂等检查
        if self.has_persons(tax_org_id):
            data = self.list_persons(tax_org_id)
            records = data.get("recordList", [])
            self.logger.info(f"[sync_persons] 已有 {len(records)} 名纳税人员，跳过")
            return {
                "action": "skipped",
                "tax_org_id": tax_org_id,
                "person_count": len(records)
            }

        # 3. 执行同步
        self.sync_report_person(tax_org_id)

        # 4. 验证
        data = self.list_persons(tax_org_id)
        records = data.get("recordList", [])
        self.logger.info(f"[sync_persons] 同步完成，当前 {len(records)} 名纳税人员")

        return {
            "action": "synced",
            "tax_org_id": tax_org_id,
            "person_count": len(records)
        }
