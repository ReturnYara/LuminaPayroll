# 用友云 API 集成说明

## 接口分析

基于 Charles 抓包，识别出两个核心接口：

### 1. 登录接口

```
GET https://c4.yonyoucloud.com/login_light
```

**参数：**
| 参数名 | 说明 | 示例值 |
|--------|------|--------|
| yhtdesturl | 目标URL | /yhtssoislogin |
| finger | 设备指纹 | 4fb3fa92d40c37c60c435e5b4d205890 |
| yhtrealservice | 真实服务地址 | https://c4.yonyoucloud.com |
| ticket | SSO票据 | ST-689644639-s67Jr3XP3P2ndkjVp5M3-online |

**关键 Cookie：**
- `at`: 访问令牌
- `yht_access_token`: 用友云访问令牌
- `JSESSIONID`: 会话ID

### 2. 切换租户接口

```
GET https://c4.yonyoucloud.com/
```

**参数：**
| 参数名 | 说明 | 示例值 |
|--------|------|--------|
| tenantId | 租户ID | ppycw2h8 |
| dimension | 维度 | ppycw2h8 |
| switch | 切换标识 | true |
| finger | 设备指纹 | 4fb3fa92d40c37c60c435e5b4d205890 |

**关键 Cookie：**
- `tenantid`: 当前租户ID
- `a00`: 租户信息（加密）

---

## 认证流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   用户登录   │────▶│  获取 Ticket │────▶│  SSO 认证   │
│  (euc.yonyou)│     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                                ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   业务操作   │◀────│  切换租户    │◀────│  获取 Cookie │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 使用方法

### 方式1：使用已有 Ticket 登录

```python
from pages.api.yonyou_api import YonyouCloudApi

api = YonyouCloudApi()

# 使用 ticket 登录（从 SSO 系统获取）
ticket = "ST-689644639-s67Jr3XP3P2ndkjVp5M3-online"
response = api.login_with_ticket(ticket)

# 切换租户
api.switch_tenant("ppycw2h8")
```

### 方式2：使用已有 Cookie

```python
from pages.api.yonyou_api import YonyouCloudApi

api = YonyouCloudApi()

# 设置已有的 cookie
cookies = {
    "at": "f85f9f83-b250-410c-b3ec-caff8f40dd54",
    "tenantid": "mq01i7yh"
}
for key, value in cookies.items():
    api.session.cookies.set(key, value)

# 直接切换租户
api.switch_tenant("ppycw2h8")
```

---

## 注意事项

1. **Ticket 是一次性的**
   - 每个 ticket 只能使用一次
   - 过期后需要重新获取

2. **Cookie 有过期时间**
   - `at` 和 `yht_access_token` 都有有效期
   - 过期后需要重新登录

3. **设备指纹**
   - `finger` 参数用于标识设备
   - 建议使用固定值保持一致性

4. **租户切换**
   - 切换租户需要已登录状态
   - 切换后会更新 `tenantid` cookie

---

## 测试运行

```bash
# 运行用友云相关测试
pytest testcases/api/test_yonyou_login.py -v

# 运行特定测试
pytest testcases/api/test_yonyou_login.py::TestYonyouCloudLogin::test_login_with_ticket -v
```

---

## 集成到 LuminaPayroll

在现有工程中，可以这样使用：

```python
# testcases/api/test_payroll_with_yonyou.py
import pytest
from pages.api.yonyou_api import YonyouCloudApi
from pages.api.payroll_api import PayrollApi

class TestPayrollWithYonyouAuth:
    """用友云认证下的薪资测试"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # 1. 用友云登录
        self.yonyou = YonyouCloudApi()
        self.yonyou.login_with_ticket("你的ticket")
        
        # 2. 切换到目标租户
        self.yonyou.switch_tenant("目标租户ID")
        
        # 3. 获取 cookie 用于薪资系统
        cookies = dict(self.yonyou.session.cookies)
        
        # 4. 初始化薪资 API（带 cookie）
        self.payroll = PayrollApi()
        # ... 使用 cookies 调用薪资接口
```
