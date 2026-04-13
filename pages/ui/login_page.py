from common.base_page import BasePage
from playwright.sync_api import Page


class LoginPage(BasePage):
    """登录页面对象"""
    
    # 元素定位器（维护在这里，便于统一管理）
    USERNAME_INPUT = "#username"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#login-btn"
    ERROR_MESSAGE = ".error-message"
    SUCCESS_TIP = ".success-tip"
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.url = "/login"
        
        # 获取测试账号配置
        self.test_accounts = self.config.get("test_accounts", {})
    
    def navigate(self):
        """导航到登录页面"""
        super().navigate(self.url)
    
    def enter_username(self, username: str = None):
        """输入用户名"""
        if username is None:
            username = self.test_accounts["admin"]["username"]
        self.fill(self.USERNAME_INPUT, username)
    
    def enter_password(self, password: str = None):
        """输入密码"""
        if password is None:
            password = self.test_accounts["admin"]["password"]
        self.fill(self.PASSWORD_INPUT, password)
    
    def click_login(self):
        """点击登录按钮"""
        self.click(self.LOGIN_BUTTON)
    
    def login(self, username: str = None, password: str = None):
        """
        完整的登录操作
        
        Args:
            username: 用户名，不传使用默认
            password: 密码，不传使用默认
        """
        self.enter_username(username)
        self.enter_password(password)
        self.click_login()
    
    def login_with_account(self, account_type: str = "admin"):
        """使用指定账号类型登录"""
        account = self.test_accounts.get(account_type, {})
        self.login(
            username=account.get("username"),
            password=account.get("password")
        )
    
    def get_error_message(self) -> str:
        """获取错误提示"""
        return self.get_text(self.ERROR_MESSAGE)
    
    def assert_login_success(self):
        """断言登录成功"""
        # 验证URL跳转
        expect(self.page).to_have_url(lambda url: "/home" in url or "/dashboard" in url)
    
    def assert_error_displayed(self):
        """断言显示错误信息"""
        expect(self.page.locator(self.ERROR_MESSAGE)).to_be_visible()