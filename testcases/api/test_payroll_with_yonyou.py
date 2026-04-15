"""
用友云认证下的薪资计算测试

使用前置 fixture 完成登录和切换租户，测试用例只关注业务逻辑
"""

import pytest
from pages.api.payroll_api import PayrollApi


class TestPayrollWithYonyouAuth:
    """
    薪资计算测试（集成用友云认证）
    
    认证流程由 fixture 自动处理：
    1. yonyou_logged_in - 自动登录
    2. yonyou_with_tenant - 自动切换租户
    3. yonyou_cookies - 获取认证 cookies
    """

    def test_calculate_payroll_with_yonyou_auth(self, yonyou_cookies):
        """
        测试薪资计算 - 使用用友云认证
        
        前置条件：
        - yonyou_cookies fixture 已完成登录和切换租户
        """
        # 初始化薪资 API
        payroll_api = PayrollApi()
        
        # 使用用友云的 cookies 调用薪资接口
        data = {
            "employeeId": "EMP001",
            "month": "2024-01",
            "baseSalary": 10000,
            "bonus": 2000
        }
        
        response = payroll_api.calculate_payroll(data, cookies=yonyou_cookies)
        
        # 验证结果
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "totalAmount" in result["data"]

    def test_get_payroll_history_with_yonyou_auth(self, yonyou_cookies):
        """
        测试获取薪资历史 - 使用用友云认证
        """
        payroll_api = PayrollApi()
        
        response = payroll_api.get_payroll_history(
            employee_id="EMP001",
            month="2024-01",
            cookies=yonyou_cookies
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    def test_update_payroll_with_yonyou_auth(self, yonyou_cookies):
        """
        测试更新薪资记录 - 使用用友云认证
        """
        payroll_api = PayrollApi()
        
        data = {
            "baseSalary": 12000,
            "bonus": 3000
        }
        
        response = payroll_api.update_payroll(
            payroll_id=123,
            data=data,
            cookies=yonyou_cookies
        )
        
        assert response.status_code == 200


class TestPayrollWithDirectYonyouApi:
    """
    直接使用 yonyou_with_tenant fixture 的测试
    """

    def test_access_yonyou_session(self, yonyou_with_tenant):
        """
        测试直接访问用友云 session
        
        可以直接使用 yonyou_with_tenant 对象调用用友云接口
        """
        # 获取当前租户ID
        current_tenant = yonyou_with_tenant.get_current_tenant()
        print(f"\n当前租户: {current_tenant}")
        
        # 验证已登录
        assert yonyou_with_tenant.is_logged_in()
        
        # 可以继续调用其他用友云接口
        # response = yonyou_with_tenant.some_other_api()

    def test_multiple_operations_with_same_auth(self, yonyou_cookies):
        """
        测试同一认证下执行多个操作
        
        同一个 yonyou_cookies 可以在多个测试中使用
        """
        payroll_api = PayrollApi()
        
        # 操作1：计算薪资
        calc_response = payroll_api.calculate_payroll(
            {"employeeId": "EMP001", "month": "2024-01", "baseSalary": 10000, "bonus": 2000},
            cookies=yonyou_cookies
        )
        assert calc_response.status_code == 200
        
        # 操作2：查询历史
        history_response = payroll_api.get_payroll_history(
            employee_id="EMP001",
            cookies=yonyou_cookies
        )
        assert history_response.status_code == 200


# ==================== 使用说明 ====================
"""
运行测试前需要设置环境变量：

export YONYOU_TICKET="ST-xxx"          # SSO ticket
export YONYOU_TENANT_ID="ppycw2h8"      # 目标租户ID

或者创建 config/yonyou_config.yaml：

ticket: "ST-xxx"
tenant_id: "ppycw2h8"

运行测试：
pytest testcases/api/test_payroll_with_yonyou.py -v

fixture 层级：
- yonyou_api: 未登录的 API 对象
- yonyou_logged_in: 已登录（session 级别，只执行一次）
- yonyou_with_tenant: 已登录+已切换租户（session 级别）
- yonyou_cookies: 获取 cookies（function 级别，每个测试独立）
"""
