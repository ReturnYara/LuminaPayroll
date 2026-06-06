"""预置工具函数

提供认证 Session 创建等通用功能
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)


def create_authenticated_session() -> requests.Session:
    """从环境变量创建已认证的 requests.Session

    需要的环境变量:
        YONYOU_COOKIE: 浏览器 DevTools 复制的完整 cookie 字符串
        YONYOU_XSRF_TOKEN: (可选) x-xsrf-token

    Returns:
        已设置 cookie 的 Session 实例
    """
    cookie_str = os.getenv("YONYOU_COOKIE", "")
    if not cookie_str:
        raise RuntimeError(
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

    logger.info(f"已加载 {len(session.cookies)} 个 cookie")
    return session
