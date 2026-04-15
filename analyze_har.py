#!/usr/bin/env python3
"""
HAR 文件分析器
用于分析从浏览器开发者工具导出的 HAR 文件
"""

import json
import sys
from pathlib import Path
from typing import List, Dict


class HarAnalyzer:
    """HAR 文件分析器"""
    
    def __init__(self, har_file: str):
        self.har_file = har_file
        self.data = self._load_har()
        self.entries = self.data.get("log", {}).get("entries", [])
    
    def _load_har(self) -> dict:
        """加载 HAR 文件"""
        with open(self.har_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def analyze(self):
        """分析 HAR 文件"""
        print("=" * 80)
        print("🔍 HAR 文件分析报告")
        print("=" * 80)
        print(f"文件: {self.har_file}")
        print(f"总请求数: {len(self.entries)}")
        
        # 筛选 API 请求（XHR/Fetch）
        api_entries = [
            e for e in self.entries 
            if e.get("_resourceType") in ["xhr", "fetch"] 
            or "/api/" in e.get("request", {}).get("url", "")
        ]
        
        print(f"API 请求数: {len(api_entries)}")
        print()
        
        # 分析每个 API 请求
        for i, entry in enumerate(api_entries, 1):
            self._print_entry(i, entry)
        
        # 生成 Python 代码
        self._generate_python_code(api_entries)
    
    def _print_entry(self, index: int, entry: dict):
        """打印单个请求详情"""
        request = entry.get("request", {})
        response = entry.get("response", {})
        
        url = request.get("url", "")
        method = request.get("method", "")
        status = response.get("status", 0)
        
        print(f"\n{'─' * 80}")
        print(f"{index}. {method} {url[:70]}")
        print(f"   状态码: {status}")
        
        # 请求头
        headers = request.get("headers", [])
        headers_dict = {h["name"]: h["value"] for h in headers}
        
        if "Content-Type" in headers_dict:
            print(f"   Content-Type: {headers_dict['Content-Type']}")
        
        if "Authorization" in headers_dict:
            auth = headers_dict["Authorization"]
            print(f"   Authorization: {auth[:50]}...")
        
        # 请求体
        post_data = request.get("postData", {})
        if post_data:
            text = post_data.get("text", "")
            if text:
                try:
                    json_data = json.loads(text)
                    print(f"   请求体: {json.dumps(json_data, ensure_ascii=False, indent=2)[:200]}")
                except:
                    print(f"   请求体: {text[:200]}")
        
        # 响应体
        response_content = response.get("content", {})
        if response_content:
            text = response_content.get("text", "")
            if text:
                try:
                    json_data = json.loads(text)
                    print(f"   响应: {json.dumps(json_data, ensure_ascii=False, indent=2)[:200]}")
                except:
                    print(f"   响应: {text[:200]}")
    
    def _generate_python_code(self, entries: List[dict]):
        """生成 Python 测试代码"""
        print("\n" + "=" * 80)
        print("🐍 生成的 Python 测试代码")
        print("=" * 80)
        
        code_lines = [
            "import requests",
            "import pytest",
            "",
            "class TestYonyouCloud:",
            '    """用友云 API 测试"""',
            "",
            "    @pytest.fixture(autouse=True)",
            "    def setup(self):",
            '        self.base_url = "https://c4.yonyoucloud.com"',
            '        self.session = requests.Session()',
            "",
        ]
        
        for entry in entries:
            request = entry.get("request", {})
            url = request.get("url", "")
            method = request.get("method", "")
            
            # 只处理 API 请求
            if "/api/" not in url:
                continue
            
            # 提取路径
            path = url.replace("https://c4.yonyoucloud.com", "")
            
            code_lines.append(f"    def test_{method.lower()}_{path.replace('/', '_').strip('_')[:30]}(self):")
            code_lines.append(f'        """{method} {path}"""')
            code_lines.append(f'        response = self.session.{method.lower()}(f"{{self.base_url}}{path}")')
            code_lines.append(f'        assert response.status_code == {entry.get("response", {}).get("status", 200)}')
            code_lines.append("")
        
        print("\n".join(code_lines))
        
        # 保存到文件
        output_file = Path(self.har_file).stem + "_generated.py"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(code_lines))
        
        print(f"\n✅ 代码已保存到: {output_file}")


def main():
    if len(sys.argv) < 2:
        print("""
使用方法:
  python3 analyze_har.py <har文件路径>

示例:
  python3 analyze_har.py ~/Downloads/c4.yonyoucloud.com.har

如何获取 HAR 文件:
  1. 打开 Chrome，按 F12 打开开发者工具
  2. 切换到 Network 标签
  3. 勾选 Preserve log
  4. 访问 https://c4.yonyoucloud.com/ 并登录
  5. 右键点击任意请求 → Save all as HAR with content
        """)
        sys.exit(1)
    
    har_file = sys.argv[1]
    analyzer = HarAnalyzer(har_file)
    analyzer.analyze()


if __name__ == "__main__":
    main()
