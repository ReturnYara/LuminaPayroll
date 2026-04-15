import requests
from typing import Dict, List, Optional
import logging


class PayfileCalculateApi:
    """发放单计算接口封装
    
    只封装两个核心接口：
    1. verifyCalculate - 验证计算条件
    2. calcalutePayDocDatas - 执行薪资计算
    
    前置接口（checkStaff → bill/save → syncPayfileDepts → syncPayfileDoc → checkFormula）
    由业务侧提前完成，本类通过参数化接收 payFileId 等关键入参。
    """

    def __init__(self, base_url: str = "https://c4.yonyoucloud.com", session: requests.Session = None):
        self.base_url = base_url
        self.session = session or requests.Session()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headers = {
            "accept": "*/*",
            "content-type": "application/json;charset=UTF-8",
            "origin": base_url,
            "referer": f"{base_url}/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "domain-key": "yonbip-hr-paybiz"
        }

    def set_xsrf_token(self, token: str):
        """设置 XSRF Token"""
        self.headers["x-xsrf-token"] = token

    def verify_calculate(self, pay_file_id: str, service_code: str = "HRXZHS_MDD_030030",
                         select_row_doc_ids: List[str] = None) -> requests.Response:
        """验证是否满足计算条件
        
        Args:
            pay_file_id: 发放单ID（由 bill/save 创建后返回）
            service_code: 服务编码
            select_row_doc_ids: 选中的发薪人员ID列表，空列表表示全部
            
        Returns:
            Response, 成功时 data.verifyResult=true
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/verifyCalculate"
        params = {"serviceCode": service_code}
        payload = {
            "payFileId": pay_file_id,
            "selectRowDocIds": select_row_doc_ids or []
        }

        self.logger.info(f"[verifyCalculate] payFileId={pay_file_id}")
        response = self.session.post(url, params=params, json=payload, headers=self.headers, verify=False)
        self.logger.info(f"[verifyCalculate] status={response.status_code}")
        return response

    def calcalute_pay_doc_datas(self, pay_file_id: str, query_id_str: str,
                                service_code: str = "HRXZHS_MDD_030030",
                                calcalute_type: int = 0,
                                select_row_doc_ids: List[str] = None,
                                page_size: int = 200, page_index: int = 1,
                                record_count: int = 0) -> requests.Response:
        """执行薪资计算
        
        Args:
            pay_file_id: 发放单ID
            query_id_str: 查询标识串（时间戳+payFileId 组合）
            service_code: 服务编码
            calcalute_type: 计算类型，0=正常计算
            select_row_doc_ids: 选中的发薪人员ID列表，空列表表示全部
            page_size: 分页大小
            page_index: 页码
            record_count: 记录总数
            
        Returns:
            Response, 成功时 data.message="计算成功!"
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/calcalutePayDocDatas"
        params = {"serviceCode": service_code}
        payload = {
            "selectRowDocIds": select_row_doc_ids or [],
            "calcaluteType": calcalute_type,
            "pageNum": 1,
            "pageSize": 999999,
            "itemReq": [],
            "billnum": "wa_pay_file_doc_list",
            "ownDomain": "yonbip-hr-paybiz",
            "serviceCode": service_code,
            "payfileId": pay_file_id,
            "queryIdStr": query_id_str,
            "onlyNoBank": False,
            "page": {
                "pageSize": page_size,
                "pageIndex": page_index,
                "recordCount": record_count
            }
        }

        self.logger.info(f"[calcalutePayDocDatas] payfileId={pay_file_id}, type={calcalute_type}")
        response = self.session.post(url, params=params, json=payload, headers=self.headers, verify=False)
        self.logger.info(f"[calcalutePayDocDatas] status={response.status_code}")
        return response

    def get_cal_progress_percent(self, pay_file_id: str,
                                  service_code: str = "HRXZHS_MDD_030030") -> requests.Response:
        """获取计算进度
        
        Args:
            pay_file_id: 发放单ID
            service_code: 服务编码
            
        Returns:
            Response, data.percentage=100 时计算完成
        """
        url = f"{self.base_url}/yonbip-hr-paybiz/pay/file/getCalProgressPercent"
        params = {
            "payfileId": pay_file_id,
            "serviceCode": service_code
        }

        response = self.session.get(url, params=params, headers=self.headers, verify=False)
        return response
