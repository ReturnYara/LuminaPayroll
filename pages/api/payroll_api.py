from common.base_api import BaseApi


class PayrollApi(BaseApi):
    """工资接口封装"""

    def __init__(self):
        super().__init__()

    def calculate_payroll(self, data: dict):
        """计算工资接口"""
        return self.post("/payroll/calculate", json=data)

    def get_payroll_history(self, employee_id: str, month: str = None):
        """获取工资历史"""
        params = {"employeeId": employee_id}
        if month:
            params["month"] = month
        return self.get("/payroll/history", params=params)

    def update_payroll(self, payroll_id: int, data: dict):
        """更新工资记录"""
        return self.put(f"/payroll/{payroll_id}", json=data)


class AuthApi(BaseApi):
    """认证接口封装"""

    def __init__(self):
        super().__init__()

    def login(self, username: str, password: str):
        """登录接口"""
        data = {
            "username": username,
            "password": password
        }
        return self.post("/auth/login", json=data)

    def logout(self):
        """登出接口"""
        return self.post("/auth/logout")
