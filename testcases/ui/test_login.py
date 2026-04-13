import pytest
from playwright.sync_api import Page
from pages.ui.login_page import LoginPage


class TestLogin:
    """登录页面测试"""
    
    def test_login_success(self, page: Page):
        """测试成功登录"""
        login_page = LoginPage(page)
        
        # 打开登录页
        login_page.navigate()
        
        # 执行登录（使用默认admin账号）
        login_page.login()
        
        # 验证登录成功
        login_page.assert_login_success()
    
    def test_login_with_normal_user(self, page: Page):
        """测试普通用户登录"""
        login_page = LoginPage(page)
        login_page.navigate()
        
        # 使用normal_user账号
        login_page.login_with_account("normal_user")
        
        login_page.assert_login_success()
    
    def test_login_failure(self, page: Page):
        """测试登录失败"""
        login_page = LoginPage(page)
        login_page.navigate()
        
        # 使用错误密码
        login_page.login_with_account("invalid_user")
        
        # 验证显示错误
        login_page.assert_error_displayed()
        error_msg = login_page.get_error_message()
        assert "用户名或密码错误" in error_msg
    
    def test_login_with_custom_input(self, page: Page):
        """测试自定义输入登录"""
        login_page = LoginPage(page)
        login_page.navigate()
        
        # 手动输入账号密码
        login_page.enter_username("test_user")
        login_page.enter_password("test_pass")
        login_page.click_login()
        
        # 根据实际结果断言
        # 这里可能是成功或失败，取决于账号是否存在
    
    def test_login_form_elements(self, page: Page):
        """测试登录表单元素"""
        login_page = LoginPage(page)
        login_page.navigate()
        
        # 验证元素存在
        expect(page.locator(login_page.USERNAME_INPUT)).to_be_visible()
        expect(page.locator(login_page.PASSWORD_INPUT)).to_be_visible()
        expect(page.locator(login_page.LOGIN_BUTTON)).to_be_visible()