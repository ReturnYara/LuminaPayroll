import pytest
import yaml
from pathlib import Path
from typing import Dict, Any


@pytest.fixture(scope="session")
def config() -> Dict[str, Any]:
    """全局配置fixture"""
    import os
    env = os.getenv("LUMINA_ENV", "dev")
    config_path = Path(__file__).parent / "config" / "environments" / f"{env}.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def test_accounts(config) -> Dict[str, Any]:
    """测试账号fixture"""
    return config.get("test_accounts", {})


@pytest.fixture(scope="session")
def api_base_url(config) -> str:
    """API基础URL"""
    return config["api_base_url"]


@pytest.fixture(scope="session")
def ui_base_url(config) -> str:
    """UI基础URL"""
    return config["ui_base_url"]


# 供其他测试文件使用的fixture
@pytest.fixture
def admin_credentials(test_accounts) -> Dict[str, str]:
    """admin账号信息"""
    return test_accounts.get("admin", {})


@pytest.fixture
def normal_user_credentials(test_accounts) -> Dict[str, str]:
    """普通用户账号信息"""
    return test_accounts.get("normal_user", {})


# ==================== 用友云认证 Fixtures ====================

@pytest.fixture(scope="session")
def yonyou_api():
    """
    用友云 API 对象（未登录状态）
    
    使用示例:
        def test_something(yonyou_api):
            yonyou_api.login_with_ticket("xxx")
    """
    from pages.api.yonyou_api import YonyouCloudApi
    return YonyouCloudApi()


@pytest.fixture(scope="session")
def yonyou_logged_in():
    """
    已登录的用友云 API 对象
    
    使用环境变量 YONYOU_TICKET 或配置中的 ticket
    
    使用示例:
        def test_something(yonyou_logged_in):
            # 已登录，直接使用
            yonyou_logged_in.switch_tenant("tenant_id")
    """
    import os
    from pages.api.yonyou_api import YonyouCloudApi
    
    api = YonyouCloudApi()
    
    # 从环境变量获取 ticket
    ticket = os.getenv("YONYOU_TICKET", "")
    
    if ticket:
        response = api.login_with_ticket(ticket)
        if response.status_code in [200, 302]:
            print(f"\n[Fixture] 用友云登录成功")
        else:
            print(f"\n[Fixture] 用友云登录失败: {response.status_code}")
    else:
        print("\n[Fixture] 警告: 未配置 YONYOU_TICKET，登录跳过")
    
    return api


@pytest.fixture(scope="session")
def yonyou_with_tenant(yonyou_logged_in):
    """
    已登录并切换到目标租户的 API 对象
    
    从环境变量 YONYOU_TENANT_ID 读取目标租户
    
    使用示例:
        def test_something(yonyou_with_tenant):
            # 已登录且已切换租户
            cookies = dict(yonyou_with_tenant.session.cookies)
            # 使用 cookies 调用业务接口
    """
    import os
    
    api = yonyou_logged_in
    
    # 获取目标租户ID
    tenant_id = os.getenv("YONYOU_TENANT_ID", "ppycw2h8")
    
    # 切换租户
    response = api.switch_tenant(tenant_id)
    
    if response.status_code in [200, 302]:
        print(f"[Fixture] 切换到租户: {tenant_id}")
    else:
        print(f"[Fixture] 切换租户失败: {response.status_code}")
    
    return api


@pytest.fixture(scope="function")
def yonyou_cookies(yonyou_with_tenant):
    """
    获取用友云的 cookies（用于传递给其他 API）
    
    使用示例:
        def test_something(yonyou_cookies):
            # 使用 cookies 调用薪资接口
            payroll_api.calculate_payroll(data, cookies=yonyou_cookies)
    """
    return dict(yonyou_with_tenant.session.cookies)