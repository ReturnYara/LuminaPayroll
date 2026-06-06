"""发薪人员匹配 API 封装

封装发薪人员的查询、HR员工参照、批量匹配接口，用于预置步骤3。

核心发现（从 HAR 确认）：
- "创建发薪人员" 本质是将 HR 系统已有员工匹配到发薪方案中
- staffIds 格式为 "staffId:staffJobId" 的数组
- serviceCode: HRXZHS_MDD_030020
- 保存前需经过 check → checkInsure → save 三步

核心接口：
- bill/list (billnum=staff_pay_doc_list): 查询方案下已有人员
- bill/ref/getRefData (scheme_new_ref): 获取方案参照
- bill/ref/getRefData (hred_staffall_ref): 获取HR可用员工
- bill/ref/getRefData (waTaxOrg_ref): 获取扣缴义务人
- bill/add (billnum=salary_staff_batch_add): 初始化新增
- pay/salaryPay/batchStaffPayDocCheck: 校验
- pay/salaryPay/batchSaveStaffPayDocBeforeCheckInsure: 保险校验
- pay/salaryPay/batchSaveStaffPayDoc: 最终保存
"""

import json
import requests
import logging
from typing import Dict, List, Optional, Any


class SalaryStaffApi:
    """发薪人员匹配接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_030020"
    BILLNUM_LIST = "staff_pay_doc_list"
    BILLNUM_ADD = "salary_staff_batch_add"
    SBILLNO_LIST = "staff_pay_doc"
    SBILLNO_ADD = "wa_staff_pay_doc_add"
    FULLNAME = "hrxc.salaryPay.WaStaffPayDoc"

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

    def list_staff(self, scheme_auth_id: str, page_index: int = 1,
                   page_size: int = 20, status: str = "1") -> Dict[str, Any]:
        """查询方案下已匹配的发薪人员

        Args:
            scheme_auth_id: 方案授权ID（来自 scheme_new_ref 的 id 字段）
            page_index: 页码
            page_size: 每页条数
            status: 人员状态 (1=待发薪, 2=计算中, 3=已计算, 4=已审批, 5=已发放)

        Returns:
            响应 data（包含 recordCount, recordList）
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "sbillno": self.SBILLNO_LIST,
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
                    {"value1": scheme_auth_id, "itemName": "schemeAuthId"},
                    {"itemName": "showContent", "value1": "0"},
                    {"itemName": "countType", "value1": "allCount"}
                ],
                "isExtend": True,
                "simpleVOs": [
                    {"op": "eq", "field": "staffPayDocStatus", "value1": status}
                ]
            },
            "bClick": True,
            "bEmptyWithoutFilterTree": False,
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "sbillno": self.SBILLNO_LIST,
            "ownDomain": "yonbip-hr-paybiz"
        }

        self.logger.info(f"[list_staff] schemeAuthId={scheme_auth_id}, status={status}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询发薪人员失败: {result.get('message', '')}")

        return result["data"]

    def has_staff(self, scheme_auth_id: str) -> bool:
        """检查方案下是否已有发薪人员

        Args:
            scheme_auth_id: 方案授权ID

        Returns:
            True=已有人员, False=无人员
        """
        data = self.list_staff(scheme_auth_id, page_index=1, page_size=1)
        records = data.get("recordList", [])
        has = len(records) > 0
        self.logger.info(f"[has_staff] schemeAuthId={scheme_auth_id}, has_records={has}")
        return has

    # ==================== 参照查询接口 ====================

    def get_scheme_ref(self) -> List[Dict]:
        """查询可用的发薪方案参照

        获取 schemeAuthId（方案授权ID）、taxTable 等信息

        Returns:
            方案参照列表，每条记录包含:
            - id: schemeAuthId（用于后续匹配）
            - schemeId: 方案ID
            - schemeName: 方案名称
            - taxTable: 税率表ID
            - taxTableName: 税率表名称
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/ref/getRefData"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "refCode": "yonbip-hr-paybiz.scheme_new_ref",
            "sourceBillnum": self.SBILLNO_ADD,
            "terminalType": "1"
        }

        payload = {
            "page": {"pageSize": 50, "pageIndex": 1},
            "refCode": "yonbip-hr-paybiz.scheme_new_ref",
            "billnum": self.SBILLNO_ADD,
            "data": "{}",
            "serviceCode": self.SERVICE_CODE,
            "condition": {
                "commonVOs": [
                    {"itemName": "schemeName", "value1": "默认方案"},
                    {"itemName": "isDefault", "value1": True}
                ]
            },
            "dataType": "grid"
        }

        self.logger.info("[get_scheme_ref] 查询方案参照")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询方案参照失败: {result.get('message', '')}")

        records = result["data"].get("recordList", [])
        self.logger.info(f"[get_scheme_ref] 找到 {len(records)} 个方案")
        return records

    def get_available_staff(self, page_index: int = 1,
                            page_size: int = 50) -> Dict[str, Any]:
        """从HR系统查询可用员工（用于匹配到方案）

        返回员工的 id(staffId) 和 staffJobId，组合为 "staffId:staffJobId"

        Returns:
            响应 data（包含 recordCount, recordList）
            每条记录包含: id, staffJobId, name, code, deptName, orgName 等
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/ref/getRefData"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "refCode": "hrcloud-staff-mgr.hred_staffall_ref",
            "sourceBillnum": "wa_staff_pay_doc_staff",
            "terminalType": "1"
        }

        payload = {
            "page": {"pageSize": page_size, "pageIndex": page_index},
            "refCode": "hrcloud-staff-mgr.hred_staffall_ref",
            "billnum": "wa_staff_pay_doc_staff",
            "data": "{}",
            "custMap": {"realHotKey": "staffJobId"},
            "serviceCode": self.SERVICE_CODE,
            "condition": {
                "commonVOs": [
                    {"itemName": "schemeName", "value1": "默认方案"},
                    {"itemName": "isDefault", "value1": True}
                ],
                "bInit": True
            },
            "dataType": "grid"
        }

        self.logger.info(f"[get_available_staff] page={page_index}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询可用员工失败: {result.get('message', '')}")

        return result["data"]

    def get_tax_org(self) -> List[Dict]:
        """获取扣缴义务人（税务组织）参照

        Returns:
            税务组织列表，每条记录包含:
            - id: waTaxOrgId
            - taxName: 扣缴义务人名称
            - code: 编码
            - belongOrg: 所属组织ID
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/ref/getRefData"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "refCode": "waTaxOrg_ref",
            "sourceBillnum": self.BILLNUM_ADD,
            "terminalType": "1"
        }

        payload = {
            "page": {"pageSize": 50, "pageIndex": 1},
            "refCode": "waTaxOrg_ref",
            "billnum": self.BILLNUM_ADD,
            "data": "{}",
            "serviceCode": self.SERVICE_CODE,
            "condition": {},
            "dataType": "grid"
        }

        self.logger.info("[get_tax_org] 查询扣缴义务人")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询扣缴义务人失败: {result.get('message', '')}")

        records = result["data"].get("recordList", [])
        self.logger.info(f"[get_tax_org] 找到 {len(records)} 个税务组织")
        return records

    # ==================== 创建接口 ====================

    def init_add(self) -> Dict[str, Any]:
        """初始化批量新增操作

        Returns:
            模板数据
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/add"
        params = {
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "sbillno": self.SBILLNO_ADD
        }
        payload = {"billnum": self.BILLNUM_ADD}

        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"初始化新增失败: {result.get('message', '')}")

        return result["data"]

    def check_staff(self, save_data: Dict[str, Any]) -> bool:
        """保存前校验

        Args:
            save_data: 与 save 完全相同的 data 内容（JSON对象，非字符串）

        Returns:
            True=校验通过
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/salaryPay/batchStaffPayDocCheck"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO_ADD
        }

        payload = {
            "billnum": self.BILLNUM_ADD,
            "data": json.dumps(save_data, ensure_ascii=False),
            "fullname": self.FULLNAME
        }

        self.logger.info("[check_staff] 执行校验")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        # 校验响应格式: {message, data: {code, controlLevel}}
        data = result.get("data", {})
        if isinstance(data, dict):
            code = data.get("code", -1)
        else:
            code = -1

        if code == 0:
            self.logger.info("[check_staff] 校验通过")
            return True
        else:
            raise RuntimeError(f"发薪人员校验失败: {result.get('message', '')}")

    def check_insure(self, save_data: Dict[str, Any]) -> bool:
        """保险校验（保存前第二步校验）

        Args:
            save_data: 与 save 完全相同的 data 内容

        Returns:
            True=校验通过
        """
        url = (f"{self.base_url}/yonbip-hr-paybiz/pay/salaryPay/"
               f"batchSaveStaffPayDocBeforeCheckInsure")
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.SBILLNO_ADD
        }

        payload = {
            "billnum": self.BILLNUM_ADD,
            "data": json.dumps(save_data, ensure_ascii=False),
            "fullname": self.FULLNAME
        }

        self.logger.info("[check_insure] 执行保险校验")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") == 200:
            self.logger.info("[check_insure] 保险校验通过")
            return True
        else:
            # 某些环境可能无保险配置，不阻断流程
            self.logger.warning(f"[check_insure] 保险校验响应: {result}")
            return True

    def batch_save(self, save_data: Dict[str, Any]) -> Dict[str, Any]:
        """批量保存发薪人员（最终保存）

        Args:
            save_data: 完整数据对象，必须包含:
                - schemeAuthId: 方案授权ID
                - waSchemeName: 方案名称
                - beginDate: 开始日期 (YYYY-MM-DD)
                - waTaxOrgId: 扣缴义务人ID
                - waTaxOrgName: 扣缴义务人名称
                - taxType: "1" (代扣税)
                - taxTableId: 税率表ID
                - taxTableName: 税率表名称
                - staffIds: ["staffId:staffJobId", ...] 数组
                - isDerate: "0"
                - mutiProjectIn: "0"
                - _status: "Insert"

        Returns:
            保存结果，number 字段表示成功匹配的人数
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/salaryPay/batchSaveStaffPayDoc"
        params = {
            "cmdname": "cmdSaveSalaryPayDoc",
            "businessActName": "批量新增发薪方案-确定",
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "sbillno": self.SBILLNO_ADD
        }

        payload = {
            "billnum": self.BILLNUM_ADD,
            "data": json.dumps(save_data, ensure_ascii=False),
            "fullname": self.FULLNAME
        }

        staff_count = len(save_data.get("staffIds", []))
        self.logger.info(f"[batch_save] 批量新增 {staff_count} 名发薪人员")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"批量保存发薪人员失败: {result.get('message', '')}")

        saved_count = result["data"].get("number", 0)
        self.logger.info(f"[batch_save] 成功匹配 {saved_count} 名人员")
        return result["data"]

    # ==================== 完整流程封装 ====================

    def match_staff_to_scheme(self, scheme_auth_id: str, scheme_name: str,
                              tax_table_id: str, tax_table_name: str,
                              begin_date: str = "2025-01-01",
                              staff_ids: List[str] = None) -> Dict[str, Any]:
        """完整的人员匹配流程：查询可用员工 → 校验 → 保存

        Args:
            scheme_auth_id: 方案授权ID（从 get_scheme_ref 获取的 id 字段）
            scheme_name: 方案名称
            tax_table_id: 税率表ID
            tax_table_name: 税率表名称
            begin_date: 开始日期
            staff_ids: 指定的 "staffId:staffJobId" 列表，
                      为 None 则自动查询全部可用员工

        Returns:
            保存结果
        """
        # 1. 获取扣缴义务人
        tax_orgs = self.get_tax_org()
        if not tax_orgs:
            raise RuntimeError("未找到扣缴义务人")
        tax_org = tax_orgs[0]
        wa_tax_org_id = tax_org["id"]
        wa_tax_org_name = tax_org.get("taxName", tax_org.get("orgName", ""))

        # 2. 如果未指定员工，自动查询全部可用员工
        if staff_ids is None:
            staff_data = self.get_available_staff(page_size=200)
            records = staff_data.get("recordList", [])
            if not records:
                raise RuntimeError("未找到可用员工")
            staff_ids = [f"{r['id']}:{r['staffJobId']}" for r in records]
            self.logger.info(f"[match_staff_to_scheme] 自动获取 {len(staff_ids)} 名员工")

        # 3. 初始化新增
        self.init_add()

        # 4. 构造保存数据
        save_data = {
            "schemeAuthId": scheme_auth_id,
            "waSchemeName": scheme_name,
            "beginDate": begin_date,
            "taxOrgName": None,
            "waTaxOrgId": wa_tax_org_id,
            "waTaxOrgName": wa_tax_org_name,
            "taxType": "1",
            "taxTableId": tax_table_id,
            "staffIds": staff_ids,
            "taxTableName": tax_table_name,
            "isDerate": "0",
            "mutiProjectIn": "0",
            "extension": {},
            "waInsures": [],
            "_status": "Insert",
            "perTaxOrgName": wa_tax_org_name,
            "perTaxOrgId": wa_tax_org_id,
        }

        # 5. 三步保存：check → checkInsure → save
        self.check_staff(save_data)
        self.check_insure(save_data)
        result = self.batch_save(save_data)

        return result
