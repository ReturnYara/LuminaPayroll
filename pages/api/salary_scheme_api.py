"""发薪方案 API 封装

封装发薪方案的查询和创建接口，用于预置步骤2。

核心接口：
- bill/list (billnum=waschemelist): 查询方案列表
- bill/add (billnum=wascheme_addcard): 获取新建模板
- bill/save: 保存创建方案
- scheme/schemeAuthDetail: 获取方案授权详情

关键参数（从 HAR 分析确认）：
- serviceCode: HRXZHS_MDD_030010
- billnum 列表: waschemelist
- billnum 新建: wascheme_addcard
"""

import json
import requests
import logging
from typing import Dict, List, Optional, Any


class SalarySchemeApi:
    """发薪方案接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_030010"
    BILLNUM_LIST = "waschemelist"
    BILLNUM_ADD_CARD = "wascheme_addcard"

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

    def list_schemes(self, page_index: int = 1, page_size: int = 20,
                     name: str = None, scheme_name: str = "默认方案",
                     enable: bool = None) -> Dict[str, Any]:
        """查询发薪方案列表

        Args:
            page_index: 页码
            page_size: 每页条数
            name: 方案名称过滤（模糊匹配）
            scheme_name: 方案名称条件（默认"默认方案"）
            enable: 是否启用过滤

        Returns:
            响应 data 字段，包含 recordCount, recordList
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "terminalType": "1"
        }

        common_vos = [
            {"itemName": "schemeName", "value1": scheme_name},
            {"itemName": "isDefault", "value1": True},
            {"value1": self.org_id, "itemName": "authBusiorg"},
        ]
        if enable is not None:
            common_vos.append({"value1": enable, "itemName": "enable"})

        payload = {
            "page": {
                "pageSize": page_size,
                "pageIndex": page_index
            },
            "billnum": self.BILLNUM_LIST,
            "condition": {
                "commonVOs": common_vos
            },
            "bClick": True,
            "bEmptyWithoutFilterTree": False,
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "ownDomain": "yonbip-hr-paybiz"
        }

        self.logger.info(f"[list_schemes] page={page_index}, name={name}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"查询发薪方案失败: {result.get('message', '')}")

        return result["data"]

    def scheme_exists(self, name: str) -> Optional[Dict]:
        """检查指定名称的发薪方案是否已存在

        通过查询列表后按 schemeName 字段精确匹配

        Args:
            name: 方案名称

        Returns:
            存在返回方案数据，不存在返回 None
        """
        data = self.list_schemes(page_index=1, page_size=50)
        record_list = data.get("recordList", [])
        for record in record_list:
            # schemeName 是列表中的方案名称字段
            record_name = record.get("schemeName", "")
            if record_name == name:
                self.logger.info(f"[scheme_exists] 方案已存在: {name}, "
                                 f"id={record.get('id')}, schemeId={record.get('schemeId')}")
                return record
        return None

    # ==================== 创建接口 ====================

    def get_add_template(self) -> Dict[str, Any]:
        """获取新建发薪方案的空白模板

        Returns:
            模板数据，包含 tenant, ytenant 等默认值
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/add"
        params = {
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "sbillno": self.BILLNUM_LIST
        }
        payload = {"billnum": self.BILLNUM_ADD_CARD}

        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"获取发薪方案模板失败: {result.get('message', '')}")

        return result["data"]

    def save_scheme(self, scheme_data: Dict[str, Any]) -> Dict[str, Any]:
        """保存（创建）发薪方案

        注意：bill/save 的 data 字段是 JSON 字符串（二次序列化）。
        创建成功后系统会自动生成 45 个默认薪资项目关联到此方案。

        Args:
            scheme_data: 方案完整数据

        Returns:
            创建结果，包含 id, schemeId, versionId 等
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/save"
        params = {
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "sbillno": self.BILLNUM_LIST,
            "orgId": self.org_id
        }

        payload = {
            "billnum": self.BILLNUM_ADD_CARD,
            "data": json.dumps(scheme_data, ensure_ascii=False)
        }

        self.logger.info(f"[save_scheme] 创建方案: {scheme_data.get('name', {}).get('zh_CN', 'unknown')}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            error_msg = result.get("message", "")
            raise RuntimeError(f"创建发薪方案失败: {error_msg}")

        data = result["data"]
        self.logger.info(f"[save_scheme] 创建成功, id={data.get('id')}, "
                         f"schemeId={data.get('schemeId')}, versionId={data.get('versionId')}")
        return data

    # ==================== 授权详情 ====================

    def get_scheme_auth_detail(self, scheme_id: str) -> str:
        """获取方案授权详情

        Args:
            scheme_id: 方案ID（bill/save 返回的 id）

        Returns:
            授权记录ID
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/scheme/schemeAuthDetail"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.BILLNUM_LIST,
            "orgId": self.org_id,
            "id": scheme_id
        }

        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"获取方案授权详情失败: {result.get('message', '')}")

        auth_id = result["data"]
        self.logger.info(f"[get_scheme_auth_detail] schemeId={scheme_id}, authId={auth_id}")
        return auth_id
