"""公共薪资项目 API 封装

封装公共薪资项目的查询、创建相关接口，用于：
1. 从标准环境导出所有薪资项目数据
2. 在目标环境中批量预置薪资项目

核心接口：
- bill/list: 分页查询薪资项目
- custom/tree/list: 获取项目分类树
- bill/add: 获取新建空白模板
- isCategoryCanBeAdd: 检查分类是否允许新增
- queryCategory: 获取分类详情
- bill/save: 保存（创建）薪资项目
"""

import json
import requests
import logging
from typing import Dict, List, Optional, Any


class SalaryItemApi:
    """公共薪资项目接口封装"""

    SERVICE_CODE = "HRXZHS_MDD_010030"
    BILLNUM_LIST = "public_wage_item"
    BILLNUM_ADD_CARD = "public_wage_item_add_card"

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

    def list_items(self, page_index: int = 1, page_size: int = 20,
                   name: str = None, scheme_name: str = "默认方案",
                   enable: bool = None) -> Dict[str, Any]:
        """分页查询公共薪资项目列表

        Args:
            page_index: 页码（从1开始）
            page_size: 每页条数
            name: 按项目名称过滤（精确匹配）
            scheme_name: 方案名称
            enable: 是否启用（True/False/None=不过滤）

        Returns:
            响应 data 字段：包含 recordCount, recordList 等
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "locale": "zh_CN",
            "terminalType": "1"
        }

        # 构造过滤条件
        common_vos = [
            {"itemName": "schemeName", "value1": scheme_name},
            {"itemName": "isDefault", "value1": True},
            {"value1": self.org_id, "itemName": "busiOrgName"},
        ]
        if enable is not None:
            common_vos.append({"value1": enable, "itemName": "enable"})
        if name:
            common_vos.append({"value1": name, "itemName": "name"})

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

        self.logger.info(f"[list_items] page={page_index}, size={page_size}, name={name}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            self.logger.error(f"[list_items] 查询失败: {result}")
            raise RuntimeError(f"查询薪资项目失败: {result.get('message', '')}")

        return result["data"]

    def list_all_items(self, page_size: int = 50, **kwargs) -> List[Dict]:
        """分页遍历导出所有薪资项目

        Returns:
            所有薪资项目的完整列表
        """
        all_items = []
        page_index = 1

        while True:
            data = self.list_items(page_index=page_index, page_size=page_size, **kwargs)
            record_list = data.get("recordList", [])
            record_count = data.get("recordCount", 0)

            all_items.extend(record_list)
            self.logger.info(f"[list_all_items] 已获取 {len(all_items)}/{record_count} 条")

            if len(all_items) >= record_count:
                break
            page_index += 1

        return all_items

    def get_category_tree(self) -> List[Dict]:
        """获取项目分类树

        Returns:
            分类树结构，每个节点包含 key(=categoryId), title(=分类名), children
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/custom/tree/list"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN"
        }
        payload = {
            "billnum": self.BILLNUM_LIST,
            "condition": {}
        }

        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"获取分类树失败: {result.get('message', '')}")

        return result["data"]

    # ==================== 创建前置接口 ====================

    def check_category_can_add(self, category_id: str) -> bool:
        """检查指定分类是否允许新增项目

        Args:
            category_id: 分类ID

        Returns:
            True=可以新增, False=不可以
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/mdd/item/isCategoryCanBeAdd"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.BILLNUM_LIST,
            "orgId": self.org_id
        }
        payload = {"id": category_id}

        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()
        return result.get("data", False)

    def get_add_template(self) -> Dict[str, Any]:
        """获取新建薪资项目的空白模板

        Returns:
            模板数据，包含默认值（busiOrg, tenant 等）
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
            raise RuntimeError(f"获取新建模板失败: {result.get('message', '')}")

        return result["data"]

    def query_category(self, category_id: str) -> Dict[str, Any]:
        """获取分类详情

        Args:
            category_id: 分类ID

        Returns:
            分类详情，包含 taxFlag, country, displaySeq 等
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/mdd/item/queryCategory"
        params = {
            "serviceCode": self.SERVICE_CODE,
            "terminalType": "1",
            "locale": "zh_CN",
            "sbillno": self.BILLNUM_LIST,
            "orgId": self.org_id
        }
        payload = {"id": category_id}

        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            raise RuntimeError(f"获取分类详情失败: {result.get('message', '')}")

        return result["data"]

    # ==================== 创建接口 ====================

    def save_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """保存（创建）一个薪资项目

        注意：bill/save 的 data 字段是 JSON 字符串（二次序列化）

        Args:
            item_data: 项目完整数据，包含 name, categoryId, dataType,
                      property, taxFlag, businessRule, waItemScopes 等

        Returns:
            服务端返回的创建结果，包含自动分配的 id 和 code
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/bill/save"
        params = {
            "cmdname": "cmdSave",
            "businessActName": "新建公共薪资项目-保存",
            "terminalType": "1",
            "serviceCode": self.SERVICE_CODE,
            "sbillno": self.BILLNUM_LIST,
            "orgId": self.org_id
        }

        # data 字段必须是 JSON 字符串
        payload = {
            "billnum": self.BILLNUM_ADD_CARD,
            "data": json.dumps(item_data, ensure_ascii=False)
        }

        self.logger.info(f"[save_item] 创建项目: {item_data.get('name', {}).get('zh_CN', 'unknown')}")
        response = self.session.post(url, params=params, json=payload,
                                     headers=self.headers, verify=False)
        result = response.json()

        if result.get("code") != 200:
            error_msg = result.get("message", "")
            name = item_data.get("name", {}).get("zh_CN", "unknown")
            self.logger.error(f"[save_item] 创建失败 [{name}]: {error_msg}")
            raise RuntimeError(f"创建薪资项目[{name}]失败: {error_msg}")

        self.logger.info(f"[save_item] 创建成功, id={result['data'].get('id')}, "
                         f"code={result['data'].get('code')}")
        return result["data"]

    # ==================== 幂等检查 ====================

    def item_exists(self, name: str) -> Optional[Dict]:
        """检查指定名称的薪资项目是否已存在

        Args:
            name: 项目名称（中文）

        Returns:
            如果存在返回项目数据，不存在返回 None
        """
        data = self.list_items(page_index=1, page_size=1, name=name)
        record_list = data.get("recordList", [])
        if record_list:
            self.logger.info(f"[item_exists] 项目已存在: {name}, id={record_list[0].get('id')}")
            return record_list[0]
        return None
