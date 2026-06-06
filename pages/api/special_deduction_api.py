"""专项附加扣除下载 API 封装

封装专项附加扣除数据下载接口，用于预置步骤5。

核心发现（从 HAR 确认）：
- serviceCode: HRXZHS_MDD_040025
- 两步下载机制：
  1. POST /specialDeduct/download — 同步触发，从税务局拉取数据
  2. POST /specialDeduct/query — 异步操作，返回 asyncKey
  3. GET /specialDeduct/getSpecialDeductDownloadProcess — 轮询异步结果
- orgId 使用 taxOrgId（税务组织ID），不是业务组织ID
- taxMonth 格式: "2025-01-01"（月份第一天）
- 查询列表: POST /specialDeduct/deductionList, billnum=special_deduct_list
- 检查是否已下载: GET /declaration/isPurchase/isDownload

核心接口：
- bill/ref/getRefData (waTaxOrg_ref): 获取税务组织
- declaration/isPurchase/isDownload: 检查是否已下载过
- specialDeduct/download: 同步触发下载
- specialDeduct/query: 异步查询（返回 asyncKey）
- specialDeduct/getSpecialDeductDownloadProcess: 轮询进度
- specialDeduct/deductionList: 查询已下载的扣除数据列表
"""

import json
import time
import requests
import logging
from typing import Dict, List, Optional, Any


class SpecialDeductionApi:
    """专项附加扣除接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_040025"
    BILLNUM_LIST = "special_deduct_list"
    BILLNUM_CARD = "special_deduct_card"
    SBILLNO = "deduct_download_tabgroup"

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com",
                 session: requests.Session = None,
                 org_id: str = "666666"):
        """
        Args:
            base_url: 环境 URL
            session: 认证 Session
            org_id: 业务组织 ID（注意：下载用的是 taxOrgId）
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
            - id: taxOrgId（用于 download/query 的 orgIds 参数）
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
            "billnum": self.BILLNUM_CARD,
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

    # ==================== 状态检查 ====================

    def is_downloaded(self, tax_org_id: str, tax_month: str) -> bool:
        """检查指定月份是否已下载过专项附加扣除数据

        Args:
            tax_org_id: 税务组织ID
            tax_month: 月份，格式 "2025-01"

        Returns:
            True=已下载过, False=未下载
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/declaration/isPurchase/isDownload"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO,
            "orgId": tax_org_id,
            "taxMonth": tax_month
        }

        self.logger.info(f"[is_downloaded] taxOrgId={tax_org_id}, taxMonth={tax_month}")
        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询下载状态失败: {result.get('message', '')}")

        # data="1" 表示已下载，data="0" 表示未下载
        downloaded = str(result.get("data", "0")) == "1"
        self.logger.info(f"[is_downloaded] result={downloaded}")
        return downloaded

    # ==================== 下载接口（同步触发） ====================

    def download(self, tax_org_id: str, tax_month: str,
                 staff_ids: List[str] = None) -> Dict[str, Any]:
        """触发从税务局下载专项附加扣除数据（同步操作）

        Args:
            tax_org_id: 税务组织ID（注意：不是业务组织ID）
            tax_month: 所属月份，格式 "2025-01-01"（月份第一天）
            staff_ids: 指定人员列表，为空则下载全部

        Returns:
            响应 data（成功时包含 message）
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/specialDeduct/download"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO
        }

        payload = {
            "orgIds": [tax_org_id],
            "taxMonth": tax_month,
            "staffIds": staff_ids or []
        }

        self.logger.info(f"[download] taxOrgId={tax_org_id}, taxMonth={tax_month}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"下载专项附加扣除失败: {result.get('message', '')}")

        self.logger.info(f"[download] 触发成功: {result['data'].get('message', '')}")
        return result["data"]

    # ==================== 异步查询 + 轮询 ====================

    def query(self, tax_org_id: str, tax_month: str) -> Dict[str, Any]:
        """发起异步查询请求（获取 asyncKey）

        Args:
            tax_org_id: 税务组织ID
            tax_month: 所属月份，格式 "2025-01-01"

        Returns:
            {"asyncKey": "ppycw2h8xxxx", "url": "/specialDeduct/getSpecialDeductDownloadProcess"}
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/specialDeduct/query"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO
        }

        payload = {
            "orgIds": [tax_org_id],
            "taxMonth": tax_month
        }

        self.logger.info(f"[query] taxOrgId={tax_org_id}, taxMonth={tax_month}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询专项附加扣除失败: {result.get('message', '')}")

        data = result["data"]
        # data 可能是嵌套结构 {"message": "...", "data": {"asyncKey": ..., "url": ...}}
        if isinstance(data, dict) and "data" in data:
            async_data = data["data"]
        else:
            async_data = data

        self.logger.info(f"[query] asyncKey={async_data.get('asyncKey', 'N/A')}")
        return async_data

    def get_download_process(self, async_key: str) -> Dict[str, Any]:
        """轮询异步下载进度

        Args:
            async_key: 从 query() 返回的 asyncKey

        Returns:
            进度信息，包含:
            - percentage: 进度（500=处理中，非0-100比例）
            - flag: 0=未完成
            - message: 状态描述
            - successCount/failCount/totalCount
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/specialDeduct/getSpecialDeductDownloadProcess"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO,
            "asyncKey": async_key
        }

        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询下载进度失败: {result.get('message', '')}")

        # data 字段可能是 JSON 字符串
        data = result.get("data", "")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                data = {"message": data, "flag": 0, "percentage": 0}

        self.logger.debug(f"[get_download_process] {data}")
        return data

    def wait_query_complete(self, tax_org_id: str, tax_month: str,
                            timeout: int = 120, interval: int = 5,
                            max_retries: int = 5) -> Dict[str, Any]:
        """等待异步查询完成

        HAR 观察到的模式：每次 query 产生一个新的 asyncKey，
        如果 poll 结果仍在处理中，可以重新发起 query 再轮询。

        Args:
            tax_org_id: 税务组织ID
            tax_month: 所属月份
            timeout: 总超时时间（秒）
            interval: 轮询间隔（秒）
            max_retries: 最多重试 query 次数

        Returns:
            最终进度信息
        """
        start_time = time.time()

        for attempt in range(1, max_retries + 1):
            if time.time() - start_time > timeout:
                self.logger.error("[wait_query_complete] 总超时")
                return {"flag": 0, "message": "timeout"}

            # 发起新的 query
            async_data = self.query(tax_org_id, tax_month)
            async_key = async_data.get("asyncKey", "")

            if not async_key:
                self.logger.warning(f"[wait_query_complete] 第{attempt}次未获得 asyncKey")
                time.sleep(interval)
                continue

            # 轮询本次 asyncKey 的进度
            time.sleep(2)  # 等待后端处理
            progress = self.get_download_process(async_key)

            flag = progress.get("flag", 0)
            percentage = progress.get("percentage", 0)
            message = progress.get("message", "")

            self.logger.info(
                f"[wait_query_complete] 第{attempt}次: flag={flag}, "
                f"percentage={percentage}, msg={message}"
            )

            # flag=1 或 percentage=1000 视为完成
            if flag == 1 or percentage == 1000:
                self.logger.info("[wait_query_complete] 查询完成")
                return progress

            # 如果有明确的错误消息但不影响继续，等一下再重试
            time.sleep(interval)

        self.logger.warning(f"[wait_query_complete] 达到最大重试次数 {max_retries}")
        return progress if 'progress' in dir() else {"flag": 0, "message": "max_retries"}

    # ==================== 数据查询 ====================

    def list_deductions(self, tax_org_id: str, tax_month_start: str,
                        tax_month_end: str, page_index: int = 1,
                        page_size: int = 50) -> Dict[str, Any]:
        """查询已下载的专项附加扣除数据列表

        Args:
            tax_org_id: 税务组织ID
            tax_month_start: 扣除月份起始，格式 "2025-01-01"
            tax_month_end: 扣除月份截止，格式 "2025-01-31"
            page_index: 页码
            page_size: 每页条数

        Returns:
            响应 data（包含 recordCount, recordList）
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/specialDeduct/deductionList"
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
                    {"value1": tax_month_start, "value2": tax_month_end,
                     "itemName": "deductMonth"}
                ],
                "isExtend": True,
                "simpleVOs": []
            },
            "serviceCode": self.SERVICE_CODE,
            "ownDomain": "yonbip-hr-paybiz"
        }

        self.logger.info(f"[list_deductions] taxOrgId={tax_org_id}, "
                         f"month={tax_month_start}~{tax_month_end}, page={page_index}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询专项附加扣除列表失败: {result.get('message', '')}")

        return result["data"]

    def has_deduction_data(self, tax_org_id: str, tax_month_start: str,
                           tax_month_end: str) -> bool:
        """检查是否已有专项附加扣除数据

        Args:
            tax_org_id: 税务组织ID
            tax_month_start: 月份起始 "2025-01-01"
            tax_month_end: 月份截止 "2025-01-31"

        Returns:
            True=已有数据, False=无数据
        """
        data = self.list_deductions(tax_org_id, tax_month_start, tax_month_end,
                                    page_index=1, page_size=1)
        records = data.get("recordList", [])
        has = len(records) > 0
        self.logger.info(f"[has_deduction_data] has={has}")
        return has

    # ==================== 完整流程封装 ====================

    def download_deductions(self, tax_org_id: str = None,
                            tax_month: str = None) -> Dict[str, Any]:
        """完整的专项附加扣除下载流程

        1. 获取税务组织（如未指定）
        2. 检查是否已下载（幂等）
        3. 触发同步下载
        4. 发起异步查询并等待完成
        5. 查询结果列表验证

        Args:
            tax_org_id: 税务组织ID，为 None 则自动查询
            tax_month: 所属月份，格式 "2025-01"，为 None 则需配置

        Returns:
            {"action": "downloaded"|"skipped", "tax_org_id": ..., "person_count": ..., ...}
        """
        # 1. 获取税务组织
        if not tax_org_id:
            tax_orgs = self.get_tax_org()
            if not tax_orgs:
                raise RuntimeError("未找到税务组织")
            tax_org_id = tax_orgs[0]["id"]
            self.logger.info(f"[download_deductions] 使用税务组织: id={tax_org_id}, "
                             f"name={tax_orgs[0].get('taxName', '')}")

        if not tax_month:
            raise RuntimeError("必须指定 tax_month 参数（格式: 2025-01）")

        # 日期格式转换
        # tax_month="2025-01" → month_first_day="2025-01-01", month_last_day="2025-01-31"
        month_first_day = f"{tax_month}-01"
        # 计算月末日期
        import calendar
        year, month = int(tax_month.split("-")[0]), int(tax_month.split("-")[1])
        last_day = calendar.monthrange(year, month)[1]
        month_last_day = f"{tax_month}-{last_day:02d}"
        # isDownload 接口用的是 "2025-01" 格式
        tax_month_short = tax_month

        # 2. 检查是否已下载过
        already_downloaded = self.is_downloaded(tax_org_id, tax_month_short)

        # 3. 检查是否已有数据（幂等）
        if self.has_deduction_data(tax_org_id, month_first_day, month_last_day):
            data = self.list_deductions(tax_org_id, month_first_day, month_last_day)
            records = data.get("recordList", [])
            self.logger.info(f"[download_deductions] 已有 {len(records)} 条扣除数据，跳过")
            return {
                "action": "skipped",
                "tax_org_id": tax_org_id,
                "tax_month": tax_month,
                "person_count": len(records),
                "already_downloaded": already_downloaded
            }

        # 4. 触发同步下载
        self.logger.info("[download_deductions] 触发下载...")
        self.download(tax_org_id, month_first_day)

        # 5. 发起异步查询并等待
        self.logger.info("[download_deductions] 发起异步查询并等待...")
        progress = self.wait_query_complete(tax_org_id, month_first_day)

        # 6. 查询结果列表
        data = self.list_deductions(tax_org_id, month_first_day, month_last_day)
        records = data.get("recordList", [])
        self.logger.info(f"[download_deductions] 下载完成，{len(records)} 条记录")

        return {
            "action": "downloaded",
            "tax_org_id": tax_org_id,
            "tax_month": tax_month,
            "person_count": len(records),
            "progress": progress
        }
