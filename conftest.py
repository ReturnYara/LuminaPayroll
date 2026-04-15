import os
import pytest
import yaml
import requests
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# 自动加载工程根目录的 .env 文件
load_dotenv(Path(__file__).parent / ".env")


@pytest.fixture(scope="session")
def config() -> Dict[str, Any]:
    """全局配置fixture"""
    env = os.getenv("LUMINA_ENV", "dev")
    config_path = Path(__file__).parent / "config" / "environments" / f"{env}.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def api_base_url(config) -> str:
    """API基础URL"""
    return config["api_base_url"]


@pytest.fixture(scope="session")
def ui_base_url(config) -> str:
    """UI基础URL"""
    return config["ui_base_url"]


# ==================== 认证 Fixtures ====================
# Cookie 通过环境变量传入，不再走登录流程
#
# 使用方式:
#   export YONYOU_COOKIE="cookieName1=value1; cookieName2=value2"
#   export YONYOU_XSRF_TOKEN="AX_xxx"
#   pytest testcases/api/test_payfile_calculate.py -v


@pytest.fixture(scope="session")
def yonyou_session() -> requests.Session:
    """
    从环境变量 YONYOU_COOKIE 构建已认证的 requests.Session

    环境变量:
        YONYOU_COOKIE: 浏览器登录后从 DevTools 复制的完整 cookie 字符串
        YONYOU_XSRF_TOKEN: (可选) x-xsrf-token 值

    使用示例:
        def test_something(yonyou_session):
            resp = yonyou_session.get("https://c4.yonyoucloud.com/...")
    """
    cookie_str = os.getenv("YONYOU_COOKIE", "")
    assert cookie_str, (
        "未设置环境变量 YONYOU_COOKIE，请先从浏览器 DevTools 复制 cookie 后执行:\n"
        '  export YONYOU_COOKIE="cookie1=val1; cookie2=val2"'
    )

    session = requests.Session()

    # 解析 cookie 字符串并设置到 session
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            session.cookies.set(key.strip(), value.strip())

    print(f"\n[Fixture] 已加载 {len(session.cookies)} 个 cookie")
    return session