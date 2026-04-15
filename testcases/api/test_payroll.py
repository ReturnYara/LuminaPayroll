import pytest
from pages.api.payroll_api import PayrollApi


class TestPayroll:
    """工资模块API测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.payroll_api = PayrollApi()

    def test_calculate_payroll(self):
        """测试工资计算"""
        data = {
            "employeeId": "EMP001",
            "month": "2024-01",
            "baseSalary": 10000,
            "bonus": 2000
        }
        response = self.payroll_api.calculate_payroll(data)
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "totalAmount" in result["data"]

    def test_get_payroll_history(self):
        """测试获取工资历史"""
        response = self.payroll_api.get_payroll_history("EMP001", "2024-01")
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert isinstance(result["data"], list)
