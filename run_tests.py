#!/usr/bin/env python3
"""
LuminaPayroll 测试运行脚本
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_api_tests():
    """运行API测试"""
    print("=" * 60)
    print("运行API测试")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        "testcases/api/",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_ui_tests(headless: bool = True):
    """运行UI测试"""
    print("=" * 60)
    print("运行UI测试")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "pytest",
        "testcases/ui/",
        "-v",
        "--tb=short"
    ]

    if headless:
        cmd.append("--headless")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_with_report():
    """运行并生成报告"""
    print("=" * 60)
    print("运行测试并生成报告")
    print("=" * 60)

    report_dir = Path(__file__).parent / "reports" / "html"
    report_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "pytest",
        "testcases/",
        "-v",
        "--html=reports/html/report.html",
        "--self-contained-html"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    if result.returncode == 0:
        print(f"\n报告已生成: {report_dir / 'report.html'}")
        import webbrowser
        webbrowser.open(f"file://{report_dir / 'report.html'}")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="LuminaPayroll 测试运行器")
    parser.add_argument(
        "--type",
        choices=["api", "ui", "all", "report"],
        default="all",
        help="测试类型"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="UI测试显示浏览器（非无头模式）"
    )

    args = parser.parse_args()

    success = True

    if args.type == "api":
        success = run_api_tests()
    elif args.type == "ui":
        success = run_ui_tests(headless=not args.headed)
    elif args.type == "report":
        success = run_with_report()
    else:
        api_success = run_api_tests()
        ui_success = run_ui_tests(headless=not args.headed)
        success = api_success and ui_success

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
