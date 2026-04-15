#!/usr/bin/env python3
"""
LuminaPayroll 测试运行器（自动启动Mock服务器）
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path


def start_mock_server():
    """启动Mock服务器"""
    print("🚀 启动Mock服务器...")
    process = subprocess.Popen(
        [sys.executable, "mock_server.py"],
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待服务器启动
    time.sleep(2)
    
    # 检查是否成功启动
    if process.poll() is None:
        print("✅ Mock服务器已启动")
        return process
    else:
        print("❌ Mock服务器启动失败")
        stdout, stderr = process.communicate()
        print(f"错误: {stderr.decode()}")
        return None


def stop_mock_server(process):
    """停止Mock服务器"""
    if process and process.poll() is None:
        print("\n🛑 停止Mock服务器...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("🧪 运行薪资计算测试（带认证）")
    print("=" * 60)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "testcases/api/test_payroll_calculate_with_auth.py",
        "-v",
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    # 启动Mock服务器
    mock_process = start_mock_server()
    if not mock_process:
        sys.exit(1)
    
    try:
        # 运行测试
        success = run_tests()
    finally:
        # 确保停止Mock服务器
        stop_mock_server(mock_process)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
