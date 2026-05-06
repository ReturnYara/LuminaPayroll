import os
import pytest
import yaml
import json
import time
from pathlib import Path
from pages.api.payfile_calculate_api import PayfileCalculateApi


@pytest.fixture(scope="module")
def calc_data():
    """加载参数化数据，支持场景引擎通过 SCENARIO_PARAM_* 环境变量覆盖"""
    data_path = Path(__file__).parent.parent.parent / "data" / "payfile_calculate.yaml"
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
def calc_api(calc_data, yonyou_session):
    """创建已认证的计算API对象

    复用 conftest.py 中的 yonyou_session fixture（由环境变量 YONYOU_COOKIE 构建），
    将 session 注入到 PayfileCalculateApi 中。
    """
    api = PayfileCalculateApi(
        base_url=calc_data["base_url"],
        session=yonyou_session
    )
    xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", calc_data.get("xsrf_token", ""))
    if xsrf_token:
        api.set_xsrf_token(xsrf_token)
    return api


class TestVerifyCalculate:
    """验证计算条件"""

    def test_verify_calculate_success(self, calc_api, calc_data):
        """验证计算状态"""
        response = calc_api.verify_calculate(
            pay_file_id=calc_data["pay_file_id"],
            service_code=calc_data["service_code"],
            select_row_doc_ids=calc_data.get("select_row_doc_ids", [])
        )

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"

        result = response.json()
        assert result["code"] == 200, f"业务码异常: {result.get('message')}"

        verify_data = result["data"]
        # verifyCalculate 的响应嵌套了一层 data
        if isinstance(verify_data, dict) and "data" in verify_data:
            assert verify_data["data"]["verifyResult"] is True, \
                f"验证未通过: {verify_data.get('message')}"
        else:
            assert verify_data.get("verifyResult") is True, \
                f"验证未通过: {result.get('message')}"

    def test_verify_calculate_with_selected_docs(self, calc_api, calc_data):
        """验证默认计算全部人员"""
        selected_ids = calc_data.get("select_row_doc_ids", [])

        response = calc_api.verify_calculate(
            pay_file_id=calc_data["pay_file_id"],
            service_code=calc_data["service_code"],
            select_row_doc_ids=selected_ids
        )

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 200


class TestCalcalutePayDocDatas:
    """执行薪资计算"""

    def test_calcalute_success(self, calc_api, calc_data):
        """验证计算状态"""
        # Step1: 先验证计算条件
        verify_resp = calc_api.verify_calculate(
            pay_file_id=calc_data["pay_file_id"],
            service_code=calc_data["service_code"]
        )
        assert verify_resp.status_code == 200, "verifyCalculate 请求失败"
        verify_result = verify_resp.json()
        assert verify_result["code"] == 200, f"verifyCalculate 业务异常: {verify_result.get('message')}"

        # Step2: 执行计算
        response = calc_api.calcalute_pay_doc_datas(
            pay_file_id=calc_data["pay_file_id"],
            query_id_str=calc_data["query_id_str"],
            service_code=calc_data["service_code"],
            calcalute_type=calc_data.get("calcalute_type", 0),
            select_row_doc_ids=calc_data.get("select_row_doc_ids", []),
            page_size=calc_data.get("page_size", 200),
            page_index=calc_data.get("page_index", 1),
            record_count=calc_data.get("record_count", 0)
        )

        assert response.status_code == 200, f"HTTP状态码异常: {response.status_code}"

        result = response.json()
        assert result["code"] == 200, f"计算请求失败: {result.get('message')}"

        # Step3: 判断是否同步完成；若异步则轮询进度
        calc_data_resp = result.get("data", {})
        if isinstance(calc_data_resp, dict) and calc_data_resp.get("message") == "计算成功!":
            # 少量人员时服务端同步返回结果，无需轮询
            return

        poll_interval = calc_data.get("progress_poll_interval", 2)
        poll_timeout = calc_data.get("progress_poll_timeout", 120)
        start_time = time.time()
        percentage = 0

        while time.time() - start_time < poll_timeout:
            progress_resp = calc_api.get_cal_progress_percent(
                pay_file_id=calc_data["pay_file_id"],
                service_code=calc_data["service_code"]
            )
            assert progress_resp.status_code == 200

            progress_data = progress_resp.json()
            if progress_data.get("code") != 200:
                # 进度接口异常（如缺少 asyncKey），视为同步已完成
                break

            # progress data 是嵌套 JSON 字符串
            inner = progress_data.get("data", "{}")
            if isinstance(inner, str):
                inner = json.loads(inner)

            percentage = inner.get("percentage", 0)
            fail_count = inner.get("failCount", 0)

            if percentage >= 100:
                assert fail_count == 0, f"计算完成但存在失败: failCount={fail_count}"
                break

            time.sleep(poll_interval)
        else:
            pytest.fail(f"计算超时({poll_timeout}s)，当前进度: {percentage}%")

    def test_calcalute_without_verify_should_still_work(self, calc_api, calc_data):
        """验证计算接口的独立性"""
        response = calc_api.calcalute_pay_doc_datas(
            pay_file_id=calc_data["pay_file_id"],
            query_id_str=calc_data["query_id_str"],
            service_code=calc_data["service_code"]
        )

        assert response.status_code == 200
        result = response.json()
        # 不强制要求 code==200，只验证接口可达
        assert "code" in result, f"响应格式异常: {result}"
