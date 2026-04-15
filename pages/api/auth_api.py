from common.base_api import BaseApi


class AuthApi(BaseApi):
    """认证接口封装"""
    
    def __init__(self):
        super().__init__()
        # 从配置中获取测试账号
        self.test_accounts = self.config.get("test_accounts", {})
    
    def login(self, username: str = None, password: str = None) -> dict:
        """
        登录接口
        
        Args:
            username: 用户名，不传则使用配置中的admin账号
            password: 密码，不传则使用配置中的admin密码
        """
        # 如果没有传参，使用默认测试账号
        if username is None:
            username = self.test_accounts["admin"]["username"]
        if password is None:
            password = self.test_accounts["admin"]["password"]
        
        data = {
            "username": username,
            "password": password
        }
        
        response = self.post("/auth/login", json=data)
        return response
    
    def login_with_account(self, account_type: str = "admin"):
        """
        使用指定账号类型登录
        
        Args:
            account_type: 账号类型 (admin/normal_user/invalid_user)
        """
        account = self.test_accounts.get(account_type, {})
        return self.login(
            username=account.get("username"),
            password=account.get("password")
        )
    
    def logout(self):
        """登出接口"""
        return self.post("/auth/logout")
    
    def get_token(self) -> str:
        """获取登录token（供其他接口使用）"""
        response = self.login()
        if response.status_code == 200:
            result = response.json()
            return result.get("data", {}).get("token", "")
        return ""
    
    def get_cookies(self) -> dict:
        """
        获取登录后的cookies（供其他接口使用）
        
        Returns:
            dict: cookies字典
        """
        # 先登录，让session保存cookies
        response = self.login()
        if response.status_code == 200:
            # 从session中获取cookies
            return dict(self.session.cookies)
        return {}
    
    def get_cookie_string(self) -> str:
        """
        获取登录后的cookie字符串（用于Header）
        
        Returns:
            str: cookie字符串，如 "sessionid=xxx; csrftoken=yyy"
        """
        cookies = self.get_cookies()
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])