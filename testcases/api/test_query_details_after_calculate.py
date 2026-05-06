import os
import pytest
import yaml
import json
import time
from pathlib import Path
from pages.api.payfile_querydetails_api import QueryPayDetailsApi

@pytest.fixture(scope="module")
def query_details_data():
    """加载参数化数据，支持场景引擎通过 SCENARIO_PARAM_* 环境变量覆盖"""
    data_path = Path(__file__).parent.parent.parent / "data" / "query_details.yaml"
    with open(data_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 场景引擎传入的参数覆盖 YAML 默认值
    prefix = "SCENARIO_PARAM_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            param_name = key[len(prefix):].lower()
            if param_name in data:
                data[param_name] = value
    return data


@pytest.fixture(scope="module")
def query_details_api(query_details_data, yonyou_session):
    """创建已认证的查询详情API对象"""
    api = QueryPayDetailsApi(
        base_url=query_details_data.get("base_url", "https://c4.yonyoucloud.com"),
        session=yonyou_session
    )
    xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")
    if xsrf_token:
        api.set_xsrf_token(xsrf_token)
    return api

class TestQueryDetailsAfterCalculate:
    """查询发放单详情"""
    """根据所得项目类型决定断言哪些项目的值
        IncItemType有10类：
        1、工资薪金所得（居民）
        2、劳务报酬（保险营销员/证券经纪人/其他连续劳务）居民
        3、劳务报酬所得（居民）
        4、全年一次性奖金所得
        5、解除劳动合同（居民）
        6、个人股权激励收入（居民）
        7、工资薪金所得（非居民）
        8、劳务报酬所得（非居民）
        9、、无住所个人数月奖金（非居民）
        10、个人股权激励（非居民）
        11、无住所个人数月奖金（非居民）
        """
    def test_query_details_after_calculate_success(self, query_details_api, query_details_data):
        """验证发放单计算结果"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"

        """获取返回参数长度，判断有几行数据"""
        for i, record in enumerate(record_list):
            """获取每行数据的所得项目类型"""
            inc_item_type = record.get("MUTIPROJECTIN4", "")
            """获取纳税月份，转成int类型"""
            tax_date = record.get("F_D_0", "")
            taxmonth = int(tax_date.split("-")[1]) if tax_date and "-" in tax_date else 0

            if inc_item_type == "工资薪金所得（居民）":
                """工资薪金所得（居民）,断言对应的项目值是否正确
                F_N_2023：累计减除费用_正常工资薪金(居民)，值应该是：纳税月*5000.00
                F_N_2031：累计收入额_正常工资薪金(居民)
                F_N_2022：累计应纳税所得额_正常工资薪金(居民)
                """
                expect1 = 5000.00 * taxmonth
                actual1 = float(record.get("F_N_2023", 0))
                assert actual1 == expect1, f"[行{i}] 累计减除费用_正常工资薪金(居民) 计算错误: 期望{expect1}, 实际{actual1}"

                expect2 = float(record.get("F_N_2031", 0)) - float(record.get("F_N_2023", 0))
                actual2 = float(record.get("F_N_2022", 0))
                assert actual2 == expect2, f"[行{i}] 累计应纳税所得额_正常工资薪金(居民) 计算错误: 期望{expect2}, 实际{actual2}"

            elif inc_item_type == "劳务报酬（保险营销员/证券经纪人/其他连续劳务）居民":
                expect1 = 5000.00 * taxmonth
                actual1 = float(record.get("F_N_2711", 0))
                assert actual1 == expect1, f"[行{i}] 累计减除费用_劳务报酬(连续劳务) 计算错误: 期望{expect1}, 实际{actual1}"

    def test_specified_sum_without_approve(self,query_details_api,query_details_data):     
        """验证不审批发放单时，指定期间合计数计算值是否正确"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"  

        for i, record in enumerate(record_list):
            """获取每行数据的指定期间合计数"""

            actual = float(record.get("F_N_29", 0))
            assert actual == 0.00

    def test_specified_avg_without_approve(self,query_details_api,query_details_data):     
        """验证不审批发放单时，指定期间平均数计算值是否正确"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"  

        for i, record in enumerate(record_list):
            """获取每行数据的指定期间合计数"""

            actual = float(record.get("F_N_30", 0))
            assert actual == 0.00

    def test_emp_info_obtain(self, query_details_api, query_details_data):
        """验证发放单计算获取员工信息集"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"

        record = record_list[0]
        actual_empCategory = record.get("F_V_1", "")  # 员工类别
        actual_empEntryDate = record.get("F_D_1", "")  # 入职日期

        assert actual_empCategory == "自有员工", f"员工类别不匹配: {actual_empCategory}"
        assert actual_empEntryDate.startswith("2025-01-01"), f"入职日期不匹配: {actual_empEntryDate}"

    def test_taxpayer_info_obtain(self, query_details_api, query_details_data):
        """验证发放单计算获取纳税人员信息集"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"

        record = record_list[0]
        actual_empEmploymentType = float(record.get("F_N_31", 0))  # 任职受雇类型
        assert actual_empEmploymentType == 1.00, f"任职受雇类型不匹配: {actual_empEmploymentType}"

    def test_Standard_Deduction(self, query_details_api, query_details_data):
        """验证发放单计算获取减除费用扣除信息集"""
        response = query_details_api.query_pay_details(query_details_data)

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result.get("data") is not None, "查询结果为空"

        record_list = result["data"].get("recordList", [])
        assert len(record_list) > 0, "发放单明细行为空"

        record = record_list[0]
        actual_Deduction_Flag = record.get("F_B_2", "")  # 按年扣除标识
        assert actual_Deduction_Flag == "否", f"按年扣除标识不匹配: {actual_Deduction_Flag}"

