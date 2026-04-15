import pytest
from pages.api.payroll_api import PayrollApi
from pages.api.auth_api import AuthApi


class TestPayrollCalculateWithAuth:
    """薪资计算接口测试（带登录认证）"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """初始化API对象"""
        self.payroll_api = PayrollApi()
        self.auth_api = AuthApi()

    def test_calculate_payroll_with_auto_login(self):
        """
        测试薪资计算 - 自动登录获取cookie
        
        流程：
        1. 自动登录获取cookie
        2. 使用cookie调用计算接口
        """
        # 计算参数
        data = {
            "employeeId": "EMP001",
            "month": "2024-01",
            "baseSalary": 10000,
            "bonus": 2000
        }
        
        # 调用计算接口（自动登录获取cookie）
        response = self.payroll_api.calculate_payroll_with_auth(data)
        
        # 验证结果
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "data" in result
        assert "totalAmount" in result["data"]

    def test_calculate_payroll_with_explicit_cookie(self):
        """
        测试薪资计算 - 显式传递cookie
        
        流程：
        1. 先登录获取cookie
        2. 将cookie作为参数传给计算接口
        """
        # 步骤1：登录获取cookie
        cookies = self.auth_api.get_cookies()
        assert cookies, "登录获取cookie失败"
        print(f"获取到的cookies: {cookies}")
        
        # 步骤2：使用cookie调用计算接口
        data = {
            "employeeId": "EMP002",
            "month": "2024-02",
            "baseSalary": 15000,
            "bonus": 3000
        }
        
        response = self.payroll_api.calculate_payroll(data, cookies=cookies)
        
        # 验证结果
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"]["totalAmount"] == 18000

    def test_calculate_payroll_without_cookie_fails(self):
        """
        测试薪资计算 - 未登录时应该失败
        """
        # 创建新的API实例（不带登录状态）
        payroll_api_no_auth = PayrollApi()
        
        data = {
            "employeeId": "EMP003",
            "month": "2024-03",
            "baseSalary": 8000,
            "bonus": 1000
        }
        
        # 不传cookie，应该返回401
        response = payroll_api_no_auth.calculate_payroll(data, cookies={})
        
        # 验证未授权
        assert response.status_code == 401

    def test_calculate_payroll_with_custom_account(self):
        """
        测试薪资计算 - 使用指定账号登录
        """
        data = {
            "employeeId": "EMP004",
            "month": "2024-04",
            "baseSalary": 12000,
            "bonus": 2500
        }
        
        # 使用normal_user账号登录并计算
        response = self.payroll_api.calculate_payroll_with_auth(
            data,
            username="user001",
            password="user123"
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    def test_calculate_and_verify_history(self):
        """
        测试计算后查询历史记录
        
        流程：
        1. 计算薪资
        2. 查询历史记录验证
        """
        employee_id = "EMP005"
        month = "2024-05"
        
        # 步骤1：计算薪资
        calculate_data = {
            "employeeId": employee_id,
            "month": month,
            "baseSalary": 20000,
            "bonus": 5000
        }
        
        calc_response = self.payroll_api.calculate_payroll_with_auth(calculate_data)
        assert calc_response.status_code == 200
        
        # 步骤2：查询历史记录
        history_response = self.payroll_api.get_payroll_history(
            employee_id=employee_id,
            month=month
        )
        
        assert history_response.status_code == 200
        result = history_response.json()
        assert result["code"] == 0
