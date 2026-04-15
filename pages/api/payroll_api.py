from common.base_api import BaseApi
from pages.api.auth_api import AuthApi


class PayrollApi(BaseApi):
    """工资接口封装"""

    def __init__(self):
        super().__init__()
        self.auth_api = AuthApi()

    def calculate_payroll(self, data: dict, cookies: dict = None):
        """
        计算工资接口
        
        Args:
            data: 计算参数
            cookies: 可选，自定义cookies。不传则自动登录获取
        """
        if cookies is None:
            cookies = self.auth_api.get_cookies()
        
        return self.post("/payroll/calculate", json=data, cookies=cookies)

    def calculate_payroll_with_auth(self, data: dict, username: str = None, password: str = None):
        """
        计算工资（自动登录获取cookie）
        
        Args:
            data: 计算参数
            username: 可选，指定用户名
            password: 可选，指定密码
        """
        # 使用指定账号或默认账号登录，获取cookies
        if username and password:
            self.auth_api.login(username, password)
        else:
            self.auth_api.login_with_account("admin")
        
        # 从auth_api的session获取cookies
        cookies = dict(self.auth_api.session.cookies)
        
        # 将cookies传递给当前请求
        return self.post("/payroll/calculate", json=data, cookies=cookies)

    def get_payroll_history(self, employee_id: str, month: str = None, cookies: dict = None):
        """获取工资历史"""
        if cookies is None:
            cookies = self.auth_api.get_cookies()
        
        params = {"employeeId": employee_id}
        if month:
            params["month"] = month
        return self.get("/payroll/history", params=params, cookies=cookies)

    def update_payroll(self, payroll_id: int, data: dict, cookies: dict = None):
        """更新工资记录"""
        if cookies is None:
            cookies = self.auth_api.get_cookies()
        
        return self.put(f"/payroll/{payroll_id}", json=data, cookies=cookies)
