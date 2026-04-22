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
def query_details_api(query_details_data):
    """创建已认证的查询详情API对象"""
    api = QueryPayDetailsApi()
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
        """查询发放单详情 - 正常场景，预期 code=200"""
        response = query_details_api.query_details(query_details_data["pay_file_id"])
        

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"
        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"
        assert result["data"] is not None, "查询结果为空"
        assert result["data"]["pay_file_id"] == query_details_data["pay_file_id"], "发放单ID不匹配"
        assert result["data"]["pay_file_name"] == query_details_data["pay_file_name"], "发放单名称不匹配"
        assert result["data"]["pay_file_date"] == query_details_data["pay_file_date"], "发放单日期不匹配"
        assert result["data"]["pay_file_amount"] == query_details_data["pay_file_amount"], "发放单金额不匹配"
        assert result["data"]["pay_file_status"] == query_details_data["pay_file_status"], "发放单状态不匹配"
        assert result["data"]["pay_file_type"] == query_details_data["pay_file_type"], "发放单类型不匹配"
        assert result["data"]["pay_file_type"] == query_details_data["pay_file_type"], "发放单类型不匹配"

        """获取返回参数长度，判断有几行数据"""
        rowlength = len(response.json()["data.recordList"])
       
        for i in range(rowlength):
            """获取每行数据的所得项目类型"""
            IncItemType = response.json()["data.recordList"][i]["MUTIPROJECTIN4"]
            """获取纳税月份，转成int类型"""
            taxmonth = int(response.json()["data.recordList[0].F_D_0"].split("-")[1])


            if IncItemType == "工资薪金所得（居民）":
                """工资薪金所得（居民）,断言对应的项目值是否正确
                f_n_2023：累计减除费用_正常工资薪金(居民)，值应该是：纳税月*5000.00
                data.recordList[0].F_N_2023
                纳税月份：data.recordList[0].F_D_0
                """
                expect1 = 5000.00 * taxmonth
                actual1 = response.json()["data"]["recordList"][i]["F_N_2023"]
                expect2 = response.json()["data.recordList[i].F_N_2031"]-response.json()["data.recordList[i].F_N_2023"]
                actual2 = response.json()["data.recordList[i].F_N_2022"]
                assert actual1 == expect1, f"累计减除费用_正常工资薪金(居民)计算错误: {expect1} != {actual1}"
                assert actual2 == expect2, f"累计应纳税所得额_正常工资薪金(居民)计算错误: {expect2} != {actual2}"
                
            elif IncItemType == "劳务报酬（保险营销员/证券经纪人/其他连续劳务）居民":
                expect1 = 5000.00 * taxmonth
                actual1 = response.json()["data"]["recordList"][i]["F_N_2711"]
              
                assert actual1 == expect1, f"累计减除费用_劳务报酬所得（其他连续劳务）计算错误: {expect1} != {actual1}"
                
            elif IncItemType == "劳务报酬所得（居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "劳务报酬所得（居民）不匹配"
            elif IncItemType == "全年一次性奖金所得":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "全年一次性奖金所得不匹配"
            elif IncItemType == "解除劳动合同（居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "解除劳动合同（居民）不匹配"
            elif IncItemType == "个人股权激励收入（居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "工资薪金所得（非居民）不匹配"
            elif IncItemType == "工资薪金所得（非居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "劳务报酬所得（非居民）不匹配"
            elif IncItemType == "劳务报酬所得（非居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "无住所个人数月奖金（非居民）不匹配"
            elif IncItemType == "无住所个人数月奖金（非居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "个人股权激励（非居民）不匹配"
            elif IncItemType == "个人股权激励（非居民）":
                assert response.json()["data.recordList"][i]["MUTIPROJECTIN4"] == query_details_data["MUTIPROJECTIN4"], "无住所个人数月奖金（非居民）不匹配"

        
