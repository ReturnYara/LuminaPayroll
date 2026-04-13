from common.base_page import BasePage
from playwright.sync_api import Page


class PayrollPage(BasePage):
    """工资计算页面对象"""

    # 元素定位器
    EMPLOYEE_ID_INPUT = "#employee-id"
    MONTH_SELECT = "#month"
    BASE_SALARY_INPUT = "#base-salary"
    BONUS_INPUT = "#bonus"
    CALCULATE_BUTTON = "#calculate-btn"
    RESULT_PANEL = "#result-panel"
    TOTAL_AMOUNT = "#total-amount"

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "/payroll/calculate"

    def navigate(self):
        """导航到工资计算页面"""
        super().navigate(self.url)

    def enter_employee_id(self, employee_id: str):
        """输入员工编号"""
        self.fill(self.EMPLOYEE_ID_INPUT, employee_id)

    def select_month(self, month: str):
        """选择月份"""
        self.page.select_option(self.MONTH_SELECT, month)

    def enter_base_salary(self, amount: str):
        """输入基本工资"""
        self.fill(self.BASE_SALARY_INPUT, amount)

    def enter_bonus(self, amount: str):
        """输入奖金"""
        self.fill(self.BONUS_INPUT, amount)

    def click_calculate(self):
        """点击计算按钮"""
        self.click(self.CALCULATE_BUTTON)

    def get_total_amount(self) -> str:
        """获取计算总额"""
        return self.get_text(self.TOTAL_AMOUNT)

    def assert_result_displayed(self):
        """断言结果显示"""
        self.assert_element_visible(self.RESULT_PANEL)


class LoginPage(BasePage):
    """登录页面对象"""

    # 元素定位器
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#login-btn"
    ERROR_MESSAGE = ".error-message"

    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "/login"

    def navigate(self):
        """导航到登录页面"""
        super().navigate(self.url)

    def login(self, username: str, password: str):
        """执行登录操作"""
        self.fill(self.USERNAME_INPUT, username)
        self.fill(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)

    def get_error_message(self) -> str:
        """获取错误信息"""
        return self.get_text(self.ERROR_MESSAGE)

    def assert_login_success(self):
        """断言登录成功"""
        self.assert_url_contains("/home")
