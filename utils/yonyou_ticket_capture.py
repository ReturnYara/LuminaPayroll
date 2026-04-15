"""
用友云 Ticket 自动获取工具

使用 Playwright 自动登录并获取 SSO ticket
"""

import asyncio
from playwright.async_api import async_playwright
from typing import Optional


async def capture_ticket(username: str, password: str, headless: bool = False) -> Optional[str]:
    """
    自动登录用友云并获取 ticket
    
    Args:
        username: 用户名/手机号
        password: 密码
        headless: 是否无头模式（False 可以看到浏览器操作）
        
    Returns:
        ticket 字符串，失败返回 None
    """
    ticket = None
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        
        # 监听所有请求，捕获包含 ticket 的 URL
        def handle_route(route, request):
            nonlocal ticket
            url = request.url
            if "ticket=" in url and "ST-" in url:
                # 提取 ticket
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if "ticket" in params:
                    ticket = params["ticket"][0]
                    print(f"\n[捕获成功] Ticket: {ticket}")
            route.continue_()
        
        page = await context.new_page()
        await page.route("**/*", handle_route)
        
        # 访问登录页面
        print("[步骤1] 打开用友云登录页面...")
        await page.goto("https://c4.yonyoucloud.com/")
        await asyncio.sleep(2)
        
        # 等待页面加载，检查是否需要登录
        print("[步骤2] 检查登录状态...")
        
        # 如果有登录表单，填写并提交
        try:
            # 等待登录表单出现（最多10秒）
            await page.wait_for_selector("input[type='text'], input[name='username'], #username", timeout=10000)
            
            print(f"[步骤3] 输入用户名: {username}")
            # 尝试多种选择器
            username_selectors = [
                "input[name='username']",
                "input[type='text']",
                "#username",
                "[placeholder*='手机' i]",
                "[placeholder*='用户' i]"
            ]
            
            for selector in username_selectors:
                try:
                    await page.fill(selector, username, timeout=2000)
                    break
                except:
                    continue
            
            print("[步骤4] 输入密码...")
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password"
            ]
            
            for selector in password_selectors:
                try:
                    await page.fill(selector, password, timeout=2000)
                    break
                except:
                    continue
            
            print("[步骤5] 点击登录按钮...")
            button_selectors = [
                "button[type='submit']",
                ".login-btn",
                "button:has-text('登录')",
                "button:has-text('Login')",
                "input[type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    break
                except:
                    continue
            
            # 等待登录完成（页面跳转）
            print("[步骤6] 等待登录完成...")
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"[提示] 可能已登录或页面结构不同: {e}")
        
        # 检查是否已获取 ticket
        if ticket:
            print(f"\n[成功] 获取到 Ticket: {ticket}")
        else:
            print("\n[失败] 未能捕获到 ticket")
            # 打印当前 URL 用于调试
            current_url = page.url
            print(f"[调试] 当前页面 URL: {current_url}")
            
            # 尝试从页面内容中提取
            if "ticket=" in current_url:
                import urllib.parse
                parsed = urllib.parse.urlparse(current_url)
                params = urllib.parse.parse_qs(parsed.query)
                ticket = params.get("ticket", [None])[0]
        
        await browser.close()
        return ticket


def get_ticket_sync(username: str, password: str, headless: bool = False) -> Optional[str]:
    """同步方式获取 ticket"""
    return asyncio.run(capture_ticket(username, password, headless))


if __name__ == "__main__":
    import os
    
    # 从环境变量或输入获取凭据
    username = os.getenv("YONYOU_USERNAME", "")
    password = os.getenv("YONYOU_PASSWORD", "")
    
    if not username or not password:
        print("请设置环境变量 YONYOU_USERNAME 和 YONYOU_PASSWORD")
        print("或者在代码中直接修改 username 和 password 变量")
        # 测试模式使用空值
        username = input("请输入用户名/手机号: ")
        password = input("请输入密码: ")
    
    ticket = get_ticket_sync(username, password, headless=False)
    
    if ticket:
        print(f"\n{'='*50}")
        print(f"Ticket: {ticket}")
        print(f"{'='*50}")
        print("\n使用方式:")
        print(f"export YONYOU_TICKET='{ticket}'")
        print("pytest testcases/api/test_payroll_with_yonyou.py -v")
