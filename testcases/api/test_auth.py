import pytest
from pages.api.auth_api import AuthApi


class TestAuth:
    """认证模块API测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前初始化"""
        self.auth_api = AuthApi()
    
    def test_login_success(self):
        """测试正常登录"""
        # 使用默认admin账号
        response = self.auth_api.login()
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "token" in result["data"]
        assert result["data"]["username"] == "admin"
    
    def test_login_with_normal_user(self):
        """测试普通用户登录"""
        response = self.auth_api.login_with_account("normal_user")
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
    
    def test_login_failure(self):
        """测试登录失败"""
        response = self.auth_api.login_with_account("invalid_user")
        
        assert response.status_code == 401
        result = response.json()
        assert result["code"] != 0
    
    def test_login_with_custom_credentials(self):
        """测试自定义账号密码登录"""
        response = self.auth_api.login(
            username="custom_user",
            password="custom_pass"
        )
        
        # 根据实际业务断言
        assert response.status_code in [200, 401]
    
    def test_logout(self):
        """测试登出"""
        # 先登录
        self.auth_api.login()
        
        # 再登出
        response = self.auth_api.logout()
        
        assert response.status_code == 200
    
    def test_get_token_for_other_api(self):
        """获取token供其他接口使用"""
        token = self.auth_api.get_token()
        
        assert token, "Token不应为空"
        print(f"获取到Token: {token[:20]}...")
        
        # 可以将token传递给其他API使用
        # other_api.set_token(token)