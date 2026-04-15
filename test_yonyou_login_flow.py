#!/usr/bin/env python3
"""
用友云登录流程测试脚本

这个脚本演示如何：
1. 使用 Playwright 自动获取 ticket
2. 使用 ticket 进行 API 登录
3. 切换租户
4. 执行业务测试
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from pages.api.yonyou_api import YonyouCloudApi, YonyouAuthHelper


def test_with_manual_ticket(ticket: str, tenant_id: str = "ppycw2h8"):
    """使用手动提供的 ticket 测试登录流程"""
    print("="*60)
    print("用友云登录流程测试")
    print("="*60)
    
    # 1. 创建 API 对象
    print("\n[1] 创建 YonyouCloudApi 对象...")
    api = YonyouCloudApi()
    
    # 2. 使用 ticket 登录
    print(f"\n[2] 使用 ticket 登录...")
    print(f"    Ticket: {ticket[:30]}...")
    response = api.login_with_ticket(ticket)
    print(f"    登录响应状态: {response.status_code}")
    print(f"    登录响应 URL: {response.url}")
    
    # 检查 cookies
    cookies = dict(api.session.cookies)
    print(f"\n[3] 当前 Cookies:")
    for key, value in cookies.items():
        print(f"    {key}: {value[:30] if len(value) > 30 else value}...")
    
    # 检查登录状态
    is_logged_in = api.is_logged_in()
    print(f"\n[4] 登录状态: {'成功' if is_logged_in else '失败'}")
    
    if not is_logged_in:
        print("\n[!] 登录失败，可能原因:")
        print("    - Ticket 已过期")
        print("    - Ticket 已被使用")
        print("    - 需要重新从浏览器获取")
        return False
    
    # 5. 切换租户
    print(f"\n[5] 切换到租户: {tenant_id}...")
    response = api.switch_tenant(tenant_id)
    print(f"    切换响应状态: {response.status_code}")
    print(f"    切换响应 URL: {response.url}")
    
    # 检查切换后的 cookies
    cookies = dict(api.session.cookies)
    print(f"\n[6] 切换后的 Cookies:")
    for key, value in cookies.items():
        print(f"    {key}: {value[:30] if len(value) > 30 else value}...")
    
    # 获取当前租户
    current_tenant = api.get_current_tenant()
    print(f"\n[7] 当前租户ID: {current_tenant}")
    
    print("\n" + "="*60)
    print("登录流程测试完成")
    print("="*60)
    
    return is_logged_in


def print_usage_instructions():
    """打印使用说明"""
    print("""
使用方法:

1. 从浏览器获取新鲜 ticket:
   - 打开 Chrome，访问 https://c4.yonyoucloud.com/
   - 完成登录
   - 按 F12 打开开发者工具 -> Network 标签
   - 找到包含 ticket 的请求（如 login_light）
   - 复制 ticket 值（格式: ST-xxxxx-xxxxx-xxxxx-online）

2. 运行测试:
   export YONYOU_TICKET="ST-xxxxx-xxxxx-xxxxx-online"
   export YONYOU_TENANT_ID="ppycw2h8"
   python3 test_yonyou_login_flow.py

3. 或者直接在代码中设置:
   修改本文件底部的 ticket 变量

注意事项:
   - Ticket 是一次性的，使用后立即失效
   - Ticket 有过期时间（通常几分钟）
   - 每次测试前需要重新获取
""")


if __name__ == "__main__":
    # 从环境变量获取 ticket
    ticket = os.getenv("YONYOU_TICKET", "")
    tenant_id = os.getenv("YONYOU_TENANT_ID", "ppycw2h8")
    
    if not ticket:
        print("[!] 错误: 未设置 YONYOU_TICKET 环境变量")
        print_usage_instructions()
        sys.exit(1)
    
    # 运行测试
    success = test_with_manual_ticket(ticket, tenant_id)
    sys.exit(0 if success else 1)
