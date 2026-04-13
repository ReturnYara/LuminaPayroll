#!/usr/bin/env python3
"""
LuminaPayroll 环境初始化脚本
"""

import subprocess
import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python版本需要 >= 3.8")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """安装依赖"""
    print("\n📦 安装依赖包...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败")
        return False


def install_playwright():
    """安装Playwright浏览器"""
    print("\n🎭 安装Playwright浏览器...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("✅ Playwright浏览器安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ Playwright浏览器安装失败")
        return False


def verify_installation():
    """验证安装"""
    print("\n🔍 验证安装...")
    try:
        import pytest
        import requests
        import yaml
        print("✅ pytest 已安装")
        print("✅ requests 已安装")
        print("✅ pyyaml 已安装")

        try:
            from playwright.sync_api import sync_playwright
            print("✅ playwright 已安装")
        except ImportError:
            print("⚠️ playwright 未安装（仅影响UI测试）")

        return True
    except ImportError as e:
        print(f"❌ 验证失败: {e}")
        return False


def main():
    print("🚀 LuminaPayroll 环境初始化")
    print("=" * 50)

    if not check_python_version():
        sys.exit(1)

    if not install_dependencies():
        sys.exit(1)

    install_playwright()

    if verify_installation():
        print("\n" + "=" * 50)
        print("✅ 环境初始化完成！")
        print("\n你可以开始运行测试:")
        print("  pytest testcases/ -v")
    else:
        print("\n⚠️ 部分组件安装失败，请检查错误信息")


if __name__ == "__main__":
    main()
