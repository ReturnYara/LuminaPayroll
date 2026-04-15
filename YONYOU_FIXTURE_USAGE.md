# 用友云认证 Fixture 使用说明

## 概述

登录和切换租户已封装为 pytest fixture，作为测试的前置条件，不需要在测试用例中编写认证逻辑。

## Fixture 层级

```
yonyou_api (session)
    └── 未登录的 API 对象
    
yonyou_logged_in (session)
    └── 已登录（自动执行登录）
    
yonyou_with_tenant (session)
    └── 已登录 + 已切换租户
    
yonyou_cookies (function)
    └── 获取认证 cookies（用于传递给其他 API）
```

## 使用方法

### 方法1：使用 yonyou_cookies（推荐）

```python
def test_something(yonyou_cookies):
    """
    测试用例只关注业务逻辑
    认证由 fixture 自动完成
    """
    payroll_api = PayrollApi()
    
    response = payroll_api.calculate_payroll(
        data={"employeeId": "EMP001", "month": "2024-01"},
        cookies=yonyou_cookies  # 使用 fixture 提供的 cookies
    )
    
    assert response.status_code == 200
```

### 方法2：使用 yonyou_with_tenant

```python
def test_something(yonyou_with_tenant):
    """
    直接操作用友云 API
    """
    # 获取当前租户
    tenant_id = yonyou_with_tenant.get_current_tenant()
    
    # 获取 cookies 传递给其他 API
    cookies = dict(yonyou_with_tenant.session.cookies)
    
    # 调用其他业务 API
    payroll_api = PayrollApi()
    response = payroll_api.calculate_payroll(data, cookies=cookies)
```

### 方法3：使用 yonyou_api（手动控制）

```python
def test_something(yonyou_api):
    """
    手动控制登录流程
    """
    # 手动登录
    yonyou_api.login_with_ticket("ST-xxx")
    
    # 手动切换租户
    yonyou_api.switch_tenant("tenant_id")
    
    # 获取 cookies
    cookies = dict(yonyou_api.session.cookies)
```

## 配置方式

### 方式1：环境变量（推荐）

```bash
export YONYOU_TICKET="ST-689644639-s67Jr3XP3P2ndkjVp5M3-online"
export YONYOU_TENANT_ID="ppycw2h8"

pytest testcases/api/test_payroll_with_yonyou.py -v
```

### 方式2：配置文件

创建 `config/yonyou_config.local.yaml`：

```yaml
ticket: "ST-xxx"
tenant_id: "ppycw2h8"
```

### 方式3：命令行参数

```python
# conftest.py 中添加
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--yonyou-ticket",
        action="store",
        default="",
        help="Yonyou SSO ticket"
    )

# fixture 中使用
@pytest.fixture(scope="session")
def yonyou_ticket(pytestconfig):
    return pytestconfig.getoption("--yonyou-ticket") or os.getenv("YONYOU_TICKET", "")
```

运行：
```bash
pytest --yonyou-ticket="ST-xxx" testcases/api/test_payroll_with_yonyou.py -v
```

## 完整示例

### 测试文件：test_payroll_with_yonyou.py

```python
import pytest
from pages.api.payroll_api import PayrollApi

class TestPayrollWithYonyouAuth:
    """
    薪资计算测试（集成用友云认证）
    """

    def test_calculate_payroll(self, yonyou_cookies):
        """测试薪资计算"""
        payroll_api = PayrollApi()
        
        data = {
            "employeeId": "EMP001",
            "month": "2024-01",
            "baseSalary": 10000,
            "bonus": 2000
        }
        
        response = payroll_api.calculate_payroll(data, cookies=yonyou_cookies)
        
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"]["totalAmount"] == 12000

    def test_get_payroll_history(self, yonyou_cookies):
        """测试获取薪资历史"""
        payroll_api = PayrollApi()
        
        response = payroll_api.get_payroll_history(
            employee_id="EMP001",
            month="2024-01",
            cookies=yonyou_cookies
        )
        
        assert response.status_code == 200
```

### 运行测试

```bash
# 设置环境变量并运行
export YONYOU_TICKET="ST-xxx"
export YONYOU_TENANT_ID="ppycw2h8"
pytest testcases/api/test_payroll_with_yonyou.py -v

# 只运行特定测试
pytest testcases/api/test_payroll_with_yonyou.py::TestPayrollWithYonyouAuth::test_calculate_payroll -v
```

## 注意事项

1. **Ticket 有效期**
   - SSO ticket 是一次性的，过期后需要重新获取
   - 从浏览器开发者工具或 Charles 抓取最新的 ticket

2. **Session 复用**
   - `yonyou_logged_in` 和 `yonyou_with_tenant` 是 session 级别的 fixture
   - 整个测试会话只执行一次登录和切换租户
   - 提高测试执行效率

3. **Cookie 隔离**
   - `yonyou_cookies` 是 function 级别的 fixture
   - 每个测试用例获取一份 cookies 副本
   - 避免测试间的相互影响

4. **失败处理**
   - 如果登录失败，fixture 会打印警告但继续执行
   - 测试用例中需要处理未认证的情况
