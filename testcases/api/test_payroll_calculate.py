import pytest
from pages.api.payroll_api import PayrollApi


class TestApiPayrollCalculate参数employeeidEmp0:
    """POST /api/payroll/calculate 参数employeeId=EMP001,mo"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.api = PayrollApi()

    def test_api_payroll_calculate_参数employeeId_EMP0(self):
        """POST /api/payroll/calculate 参数employeeId=EMP001,month=2024-01 验证状态码200 验证返回data."""
        # 设置请求参数
        params = {'employeeId': 'EMP001'}
        # 发送POST请求
        response = self.api.post("/api/payroll/calculate", params=params)
        # 验证状态码
        assert response.status_code == 200
        # 验证响应数据
        result = response.json()
        # TODO: 验证: data
        # 添加更多断言...

