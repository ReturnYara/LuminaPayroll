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