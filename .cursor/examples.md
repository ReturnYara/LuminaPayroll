# Cursor AI 对话示例

## 示例 1：生成 API 测试用例

**用户输入：**
```
帮我生成一个测试员工信息查询接口的用例，接口是 GET /api/employee/info，需要传入 employeeId 参数，验证返回的数据包含 name、department、position 字段
```

**AI 生成：**
```python
import pytest
from pages.api.employee_api import EmployeeApi


class TestEmployeeInfo:
    """员工信息查询测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.api = EmployeeApi()

    def test_get_employee_info(self):
        """测试获取员工信息"""
        employee_id = "EMP001"
        response = self.api.get(f"/api/employee/info?employeeId={employee_id}")
        
        # 验证状态码
        assert response.status_code == 200
        
        # 验证响应结构
        result = response.json()
        assert result["code"] == 0
        assert "data" in result
        
        # 验证必要字段
        data = result["data"]
        assert "name" in data, "返回数据缺少 name 字段"
        assert "department" in data, "返回数据缺少 department 字段"
        assert "position" in data, "返回数据缺少 position 字段"
        
        # 验证字段不为空
        assert data["name"], "name 字段不能为空"
        assert data["department"], "department 字段不能为空"
        assert data["position"], "position 字段不能为空"
```

---

## 示例 2：生成 UI 测试用例

**用户输入：**
```
生成一个测试登录页面的用例：打开登录页，输入错误的用户名和密码，点击登录，验证显示错误提示
```

**AI 生成：**
```python
import pytest
from playwright.sync_api import Page
from pages.ui.login_page import LoginPage


class TestLoginFailure:
    """登录失败测试"""

    def test_login_with_wrong_credentials(self, page: Page):
        """测试使用错误的凭据登录"""
        login_page = LoginPage(page)
        
        # 打开登录页面
        login_page.navigate()
        
        # 输入错误的用户名和密码
        login_page.fill(login_page.USERNAME_INPUT, "wrong_user")
        login_page.fill(login_page.PASSWORD_INPUT, "wrong_password")
        
        # 点击登录按钮
        login_page.click(login_page.LOGIN_BUTTON)
        
        # 验证显示错误提示
        error_message = login_page.get_error_message()
        assert error_message, "应该显示错误提示"
        assert "用户名或密码错误" in error_message or "登录失败" in error_message
```

---

## 示例 3：解释现有代码

**用户输入：**
```
解释这段代码的作用和工作原理
```

**AI 解释：**
这段代码是一个 API 测试用例，使用 pytest 框架和 PO（Page Object）模式：

1. **类定义**：`TestPayroll` 继承自 object，是测试类的标准写法
2. **Fixture**：`setup` 方法使用 `@pytest.fixture(autouse=True)` 装饰器，表示每个测试方法执行前都会自动运行
3. **API 初始化**：在 setup 中创建 `PayrollApi` 实例，用于发送 HTTP 请求
4. **测试方法**：`test_calculate_payroll` 是实际的测试用例
5. **请求数据**：构造包含员工ID、月份、基本工资和奖金的请求体
6. **发送请求**：调用 `calculate_payroll` 方法发送 POST 请求
7. **断言验证**：
   - 验证 HTTP 状态码为 200
   - 验证业务状态码为 0（表示成功）
   - 验证返回数据包含 `totalAmount` 字段

---

## 示例 4：重构为参数化测试

**用户输入：**
```
将上面的测试重构为参数化测试，支持测试多组不同的员工数据
```

**AI 生成：**
```python
import pytest
from pages.api.payroll_api import PayrollApi


class TestPayroll:
    """工资模块API测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.api = PayrollApi()

    @pytest.mark.parametrize("employee_id,month,base_salary,bonus,expected_total", [
        ("EMP001", "2024-01", 10000, 2000, 12000),
        ("EMP002", "2024-01", 15000, 3000, 18000),
        ("EMP003", "2024-02", 8000, 1000, 9000),
    ])
    def test_calculate_payroll(self, employee_id, month, base_salary, bonus, expected_total):
        """测试工资计算 - 参数化"""
        data = {
            "employeeId": employee_id,
            "month": month,
            "baseSalary": base_salary,
            "bonus": bonus
        }
        response = self.api.calculate_payroll(data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "totalAmount" in result["data"]
        assert result["data"]["totalAmount"] == expected_total
```

---

## 示例 5：添加异常处理

**用户输入：**
```
为这个测试添加异常处理，当接口返回非200状态码时给出更详细的错误信息
```

**AI 生成：**
```python
import pytest
from requests.exceptions import RequestException
from pages.api.payroll_api import PayrollApi


class TestPayroll:
    """工资模块API测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.api = PayrollApi()

    def test_calculate_payroll(self):
        """测试工资计算 - 带异常处理"""
        data = {
            "employeeId": "EMP001",
            "month": "2024-01",
            "baseSalary": 10000,
            "bonus": 2000
        }
        
        try:
            response = self.api.calculate_payroll(data)
            
            # 验证状态码
            assert response.status_code == 200, \
                f"期望状态码 200，实际返回 {response.status_code}，响应内容：{response.text}"
            
            # 解析响应
            try:
                result = response.json()
            except ValueError as e:
                pytest.fail(f"响应不是有效的 JSON 格式：{response.text}")
            
            # 验证业务码
            assert result.get("code") == 0, \
                f"业务处理失败，code={result.get('code')}, message={result.get('message', '未知错误')}"
            
            # 验证数据
            assert "data" in result, "响应缺少 data 字段"
            assert "totalAmount" in result["data"], "data 中缺少 totalAmount 字段"
            
        except RequestException as e:
            pytest.fail(f"请求发送失败：{str(e)}")
```
