# 用友云登录测试指南

## 问题总结

之前的测试失败是因为从 Charles 抓取的 ticket 已经过期/被使用。Ticket 是一次性的，使用后立即失效。

## 获取新鲜 Ticket 的方法

### 方法1: 浏览器开发者工具（推荐）

1. **打开浏览器**，访问 https://c4.yonyoucloud.com/

2. **完成登录流程**

3. **按 F12 打开开发者工具**
   - 切换到 **Network** (网络) 标签
   - 勾选 **Preserve log** (保留日志)

4. **找到包含 ticket 的请求**
   - 查找 URL 包含 `login_light` 或 `ticket=` 的请求
   - 点击该请求，查看详细信息

5. **复制 ticket**
   - 在 Request URL 中找到 `ticket=ST-xxxxx-xxxxx-xxxxx-online`
   - 复制完整的 ticket 值

### 方法2: Charles 代理（之前使用的方法）

1. 打开 Charles 代理
2. 访问 https://c4.yonyoucloud.com/ 并登录
3. 在 Charles 中找到登录相关的请求
4. 右键点击请求 -> Copy cURL
5. 从 cURL 中提取 ticket 参数

### 方法3: 使用 Playwright 自动获取（已创建脚本）

```bash
# 设置凭据
export YONYOU_USERNAME="你的手机号"
export YONYOU_PASSWORD="你的密码"

# 运行自动获取脚本
python3 utils/yonyou_ticket_capture.py
```

注意：此方法需要页面元素选择器正确，可能需要根据实际页面调整。

## 运行测试

### 快速测试登录流程

```bash
# 设置环境变量
export YONYOU_TICKET="ST-xxxxx-xxxxx-xxxxx-online"
export YONYOU_TENANT_ID="ppycw2h8"

# 运行登录流程测试
python3 test_yonyou_login_flow.py
```

### 运行完整测试套件

```bash
# 设置环境变量
export YONYOU_TICKET="ST-xxxxx-xxxxx-xxxxx-online"
export YONYOU_TENANT_ID="ppycw2h8"

# 运行 pytest 测试
python3 -m pytest testcases/api/test_payroll_with_yonyou.py -v
```

## 代码结构说明

### Fixtures（conftest.py）

- `yonyou_api`: 未登录的 API 对象
- `yonyou_logged_in`: 已登录的 API 对象（使用 ticket）
- `yonyou_with_tenant`: 已登录并切换租户的 API 对象
- `yonyou_cookies`: 获取登录后的 cookies

### API 封装（pages/api/yonyou_api.py）

```python
class YonyouCloudApi:
    def login_with_ticket(self, ticket: str) -> Response
    def switch_tenant(self, tenant_id: str) -> Response
    def is_logged_in(self) -> bool
    def get_current_tenant(self) -> str
```

### 测试示例

```python
def test_with_yonyou_auth(yonyou_cookies):
    # yonyou_cookies 会自动完成登录和切换租户
    # 使用 cookies 调用业务接口
    response = requests.post(
        "https://c4.yonyoucloud.com/api/payroll/calculate",
        cookies=yonyou_cookies,
        json={...}
    )
    assert response.status_code == 200
```

## 注意事项

1. **Ticket 是一次性的** - 每次测试都需要新的 ticket
2. **Ticket 有过期时间** - 通常几分钟内有效
3. **SSL 验证已临时禁用** - 用于测试环境，生产环境应启用
4. **当前使用 verify=False** - 在 yonyou_api.py 中可修改

## 下一步建议

1. 获取新鲜 ticket
2. 运行 `python3 test_yonyou_login_flow.py` 验证登录
3. 运行 pytest 测试套件
4. 如需自动化获取 ticket，完善 `utils/yonyou_ticket_capture.py` 中的选择器
