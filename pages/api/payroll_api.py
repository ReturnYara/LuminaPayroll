from common.base_api import BaseApi


class PayrollApi(BaseApi):
    """工资接口封装"""

    def __init__(self):
        super().__init__()

    def calculate_payroll(self, data: dict, cookies: dict = None):
        """
        计算工资接口
        
        Args:
            data: 计算参数
            cookies: 认证cookies（从环境变量 YONYOU_COOKIE 获取）
        """
        return self.post("/payroll/calculate", json=data, cookies=cookies)

    def get_payroll_history(self, employee_id: str, month: str = None, cookies: dict = None):
        """获取工资历史"""
        params = {"employeeId": employee_id}
        if month:
            params["month"] = month
        return self.get("/payroll/history", params=params, cookies=cookies)

    def update_payroll(self, payroll_id: int, data: dict, cookies: dict = None):
        """更新工资记录"""
        return self.put(f"/payroll/{payroll_id}", json=data, cookies=cookies)
