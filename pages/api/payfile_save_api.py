import json
import requests
from typing import Dict, List, Optional
import logging


class PayfileSaveApi:
    """发放单保存接口封装 (bill/save)

    封装 POST /yonbip-hr-paybiz/bill/save 接口。
    该接口用于创建 / 保存薪资发放单，返回的 data.id 即为后续
    syncPayfileDepts / syncPayfileDoc / verifyCalculate / calcalutePayDocDatas
    等接口所需的 payFileId。
    """

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com",
                 session: requests.Session = None):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json;charset=UTF-8",
            "origin": base_url,
            "referer": f"{base_url}/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "domain-key": "yonbip-hr-paybiz",
        }

    def set_xsrf_token(self, token: str):
        """设置 XSRF Token"""
        self.headers["x-xsrf-token"] = token

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    def save(self,
             billnum: str,
             data: Dict,
             service_code: str = "HRXZHS_MDD_030030",
             transi_type_id: str = "",
             transi_type_code: str = "payFileApprove",
             transi_type_name: str = "新建发放单",
             org_id: str = "",
             ) -> requests.Response:
        """保存发放单

        Args:
            billnum: 单据编号，默认 "wa_pay_file_card"
            data: 发放单业务数据字典，包含以下关键字段：
                - tenant / ytenant: 租户标识
                - busiOrg / busiOrgVid: 业务组织 ID
                - orgName: 组织名称
                - waSchemeId / pkWaScheme / pkWaSchemeName: 薪资方案
                - periodRuleId: 期间规则 ID
                - payPeriod / payPeriodName: 薪资期间
                - taxMonth: 税月
                - currency / currencyName: 币种
                - name: 多语言名称 {"zh_CN": ..., "en_US": ..., "zh_TW": ...}
                - payDate: 发放日期
                - code: 发放单编码
                - transiTypeCode / transiTypeId / transiTypeName: 交易类型
                - items: 薪资项目列表
            service_code: 服务编码
            transi_type_id: 交易类型 ID（同时作为 URL 参数 transtype / stranstype）
            transi_type_code: 交易类型编码
            transi_type_name: 交易类型名称
            org_id: 业务组织 ID（URL 参数）

        Returns:
            Response 对象。
            成功时 code=200, data.id 为新建的发放单 ID (payFileId)。
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/save"
        params = {
            "cmdname": "cmdSave",
            "businessActName": "薪资发放单-保存",
            "terminalType": "1",
            "serviceCode": service_code,
            "transiTypeId": transi_type_id,
            "transiTypeCode": transi_type_code,
            "transiTypeName": transi_type_name,
            "transtype": transi_type_id,
            "sbillno": "wa_pay_file_list",
            "orgId": org_id,
        }

        # bill/save 的 data 字段在 HAR 中是 JSON 字符串（stringified JSON）
        payload = {
            "billnum": billnum,
            "data": json.dumps(data, ensure_ascii=False),
        }

        self.logger.info(
            f"[bill/save] billnum={billnum}, "
            f"code={data.get('code')}, orgName={data.get('orgName')}"
        )
        response = self.session.post(
            url, params=params, json=payload,
            headers=self.headers, verify=False,
        )
        self.logger.info(f"[bill/save] status={response.status_code}")
        return response

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def build_data(
        tenant: str,
        ytenant: str,
        busi_org: str,
        busi_org_vid: str,
        org_name: str,
        wa_scheme_id: str,
        pk_wa_scheme: str,
        pk_wa_scheme_name: str,
        period_rule_id: str,
        pay_period: str,
        pay_period_name: str,
        tax_month: str,
        currency: str,
        currency_name: str,
        name_zh_cn: str,
        name_en_us: str,
        name_zh_tw: str,
        pay_date: str,
        code: str,
        transi_type_code: str = "payFileApprove",
        transi_type_id: str = "",
        transi_type_name: str = "新建发放单",
        items: List[Dict] = None,
    ) -> Dict:
        """根据参数构造 data 字典

        提供一个更友好的方式来组装 data，避免调用方自行拼字典。
        """
        return {
            "tenant": tenant,
            "ytenant": ytenant,
            "busiOrg": busi_org,
            "busiOrgVid": busi_org_vid,
            "orgName": org_name,
            "waSchemeId": wa_scheme_id,
            "pkWaScheme": pk_wa_scheme,
            "pkWaSchemeName": pk_wa_scheme_name,
            "periodRuleId": period_rule_id,
            "salaryGroupName": "",
            "payPeriod": pay_period,
            "payPeriodName": pay_period_name,
            "taxMonth": tax_month,
            "currency": currency,
            "currencyName": currency_name,
            "name": {
                "zh_CN": name_zh_cn,
                "en_US": name_en_us,
                "zh_TW": name_zh_tw,
            },
            "payDate": pay_date,
            "code": code,
            "isWfControlled": "1",
            "payfileCharacter": {},
            "transiTypeCode": transi_type_code,
            "transiTypeId": transi_type_id,
            "transiTypeName": transi_type_name,
            "verifystate": 0,
            "isHistoricalTaxPeriod": "0",
            "_status": "Insert",
            "isCopy": False,
            "copyId": None,
            "items": items or [],
        }

    @staticmethod
    def extract_pay_file_id(response: requests.Response) -> str:
        """从 save 响应中提取 payFileId

        Args:
            response: save 接口的 Response 对象

        Returns:
            发放单 ID 字符串

        Raises:
            ValueError: 响应异常或缺少 id 字段
        """
        result = response.json()
        if result.get("code") != 200:
            raise ValueError(f"save 接口业务异常: {result.get('message')}")
        data = result.get("data", {})
        pay_file_id = data.get("id")
        if not pay_file_id:
            raise ValueError(f"save 响应缺少 data.id: {result}")
        return str(pay_file_id)
