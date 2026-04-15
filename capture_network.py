#!/usr/bin/env python3
"""
网络请求抓取工具
用于抓取登录和切换租户过程中的接口调用
"""

import json
from playwright.sync_api import sync_playwright
from typing import List, Dict


class NetworkCapture:
    """网络请求抓取器"""
    
    def __init__(self):
        self.requests: List[Dict] = []
        self.responses: List[Dict] = []
    
    def capture_request(self, request):
        """捕获请求"""
        try:
            req_info = {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "post_data": request.post_data if request.post_data else None,
                "resource_type": request.resource_type,
                "timestamp": request.timing.get("startTime", 0) if hasattr(request, "timing") else 0
            }
            self.requests.append(req_info)
            print(f"[REQUEST] {request.method} {request.url[:80]}...")
        except Exception as e:
            print(f"[ERROR] 捕获请求失败: {e}")
    
    def capture_response(self, response):
        """捕获响应"""
        try:
            request = response.request
            resp_info = {
                "method": request.method,
                "url": request.url,
                "status": response.status,
                "status_text": response.status_text,
                "headers": dict(response.headers),
                "request_headers": dict(request.headers),
                "resource_type": request.resource_type
            }
            self.responses.append(resp_info)
            print(f"[RESPONSE] {response.status} {request.method} {request.url[:80]}...")
        except Exception as e:
            print(f"[ERROR] 捕获响应失败: {e}")
    
    def save_to_file(self, filename: str = "captured_requests.json"):
        """保存抓取的请求到文件"""
        data = {
            "requests": self.requests,
            "responses": self.responses,
            "summary": {
                "total_requests": len(self.requests),
                "total_responses": len(self.responses)
            }
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 已保存到文件: {filename}")
        print(f"   请求数: {len(self.requests)}")
        print(f"   响应数: {len(self.responses)}")
    
    def print_api_summary(self):
        """打印API摘要"""
        print("\n" + "="*60)
        print("📊 抓取到的API接口摘要")
        print("="*60)
        
        # 按资源类型分组
        api_requests = [r for r in self.requests if r["resource_type"] in ["xhr", "fetch", "document"]]
        
        for i, req in enumerate(api_requests, 1):
            print(f"\n{i}. {req['method']} {req['url'][:100]}")
            if req['post_data']:
                print(f"   请求体: {req['post_data'][:200]}...")


def capture_login_flow():
    """
    抓取登录流程中的网络请求
    
    使用说明:
    1. 脚本会自动打开浏览器
    2. 你需要手动输入账号密码登录
    3. 登录成功后按回车继续
    4. 手动切换租户
    5. 按回车结束抓取
    """
    capture = NetworkCapture()
    
    with sync_playwright() as p:
        # 启动浏览器（非无头模式，方便手动操作）
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        
        # 创建页面
        page = context.new_page()
        
        # 监听网络请求
        page.on("request", capture.capture_request)
        page.on("response", capture.capture_response)
        
        print("🚀 正在打开登录页面...")
        print("   URL: https://c4.yonyoucloud.com/")
        
        # 访问目标网站
        page.goto("https://c4.yonyoucloud.com/")
        
        print("\n" + "="*60)
        print("📢 请按以下步骤操作:")
        print("="*60)
        print("1. 在浏览器中输入账号密码登录")
        print("2. 登录成功后，回到这里按回车键")
        print("="*60)
        
        input("\n按回车键继续（登录完成后）...")
        
        print("\n📢 现在请切换租户，然后回到这里按回车键")
        input("按回车键结束抓取...")
        
        # 保存结果
        capture.save_to_file("captured_requests.json")
        capture.print_api_summary()
        
        # 关闭浏览器
        browser.close()
        
        return capture


def analyze_captured_apis(filename: str = "captured_requests.json"):
    """分析抓取到的API"""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("\n" + "="*60)
    print("🔍 API 分析报告")
    print("="*60)
    
    # 筛选XHR/Fetch请求
    api_calls = [r for r in data["requests"] if r["resource_type"] in ["xhr", "fetch"]]
    
    # 按域名分组
    domains = {}
    for req in api_calls:
        url = req["url"]
        domain = url.split("/")[2] if "/" in url else "unknown"
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(req)
    
    for domain, requests in domains.items():
        print(f"\n📍 域名: {domain}")
        print("-" * 40)
        for req in requests:
            print(f"  {req['method']:6} {req['url'][:80]}")
            if req.get("post_data"):
                try:
                    # 尝试解析JSON
                    post_json = json.loads(req["post_data"])
                    print(f"         参数: {json.dumps(post_json, ensure_ascii=False)[:100]}")
                except:
                    print(f"         参数: {req['post_data'][:100]}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        # 分析已抓取的数据
        analyze_captured_apis()
    else:
        # 执行抓取
        print("""
╔══════════════════════════════════════════════════════════╗
║           网络请求抓取工具 - 用友云登录流程              ║
╚══════════════════════════════════════════════════════════╝

这个工具会:
1. 打开浏览器访问 https://c4.yonyoucloud.com/
2. 抓取所有网络请求（包括登录、切换租户等）
3. 保存到 captured_requests.json 文件

使用方法:
- 直接运行: 抓取新的请求
- 运行 analyze: 分析已抓取的数据
        """)
        
        capture_login_flow()
