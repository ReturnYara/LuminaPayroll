import pytest
from playwright.sync_api import Page
from pages.ui.payroll_page import PayrollPage, LoginPage


class TestPayrollPage:
    """工资计算页面测试"""

    def test_calculate_payroll(self, page: Page):
        """测试工资计算功能"""
        payroll_page = PayrollPage(page)
        payroll_page.navigate()
        payroll_page.enter_employee_id("EMP001")
        payroll_page.select_month("2024-01")
        payroll_page.enter_base_salary("10000")
        payroll_page.enter_bonus("2000")
        payroll_page.click_calculate()
        payroll_page.assert_result_displayed()
        total = payroll_page.get_total_amount()
        assert "12000" in total


class TestLogin:
    """登录页面测试"""

    def test_login_success(self, page: Page):
        """测试成功登录"""
        login_page = LoginPage(page)
        login_page.navigate()
        login_page.login("admin", "admin123")
        login_page.assert_login_success()

    def test_login_failure(self, page: Page):
        """测试登录失败"""
        login_page = LoginPage(page)
        login_page.navigate()
        login_page.login("admin", "wrong_password")
        error_msg = login_page.get_error_message()
        assert "用户名或密码错误" in error_msg
