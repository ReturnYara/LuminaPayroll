import os
import json
import pytest
import yaml
import requests
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv

# 自动加载工程根目录的 .env 文件
load_dotenv(Path(__file__).parent / ".env")


# ==================== 请求拦截器 ====================

_request_log: List[Dict] = []


def _capture_response(response, *args, **kwargs):
    """Session 钩子：捕获每次接口调用的请求和响应摘要"""
    req = response.request
    body = ""
    if req.body:
        try:
            body = req.body.decode("utf-8") if isinstance(req.body, bytes) else str(req.body)
            # 尝试格式化 JSON
            parsed = json.loads(body)
            body = json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    resp_body = ""
    try:
        resp_body = json.dumps(response.json(), indent=2, ensure_ascii=False)
    except Exception:
        resp_body = response.text[:500] if response.text else ""

    _request_log.append({
        "method": req.method,
        "url": req.url,
        "request_body": body,
        "status_code": response.status_code,
        "response_body": resp_body,
    })


# ==================== 自定义报告钩子 ====================

_lumina_results = []
_lumina_scenarios = []
_lumina_start_time = None


def pytest_configure(config):
    """pytest 启动时初始化"""
    global _lumina_start_time
    _lumina_start_time = datetime.now()
    _lumina_results.clear()
    _lumina_scenarios.clear()


@pytest.fixture(autouse=True)
def _capture_requests_per_test():
    """每个测试用例执行前清空请求日志，执行后保留数据供报告采集"""
    _request_log.clear()
    yield


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_logreport(report):
    """收集每个测试用例的执行结果 + 失败时附带请求回放数据"""
    if report.when == "call" or (report.when == "setup" and report.skipped):
        requests_data = list(_request_log) if report.outcome == "failed" else []
        _lumina_results.append({
            "nodeid": report.nodeid,
            "outcome": report.outcome,
            "duration": round(report.duration, 2),
            "error": str(report.longrepr)[:500] if report.longrepr else "",
            "requests": requests_data
        })

        # 子进程模式下，失败时将请求日志写入临时文件供主进程读取
        if os.getenv("LUMINA_SUBPROCESS") == "1" and report.outcome == "failed":
            log_path = os.getenv("LUMINA_REQUEST_LOG_PATH", "")
            if log_path and requests_data:
                try:
                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(requests_data, f, ensure_ascii=False)
                except Exception:
                    pass


def pytest_sessionfinish(session, exitstatus):
    """测试结束后生成自定义 HTML 报告（仅主进程执行，子进程跳过）"""
    if os.getenv("LUMINA_SUBPROCESS") == "1":
        return

    from common.report_generator import ReportGenerator

    if not _lumina_results:
        return

    generator = ReportGenerator()
    generator.set_timing(_lumina_start_time, datetime.now())

    for r in _lumina_results:
        # 跳过场景包装用例（test_scenario），其步骤会从 _lumina_scenarios 展开
        if "test_scenario" in r["nodeid"] and _lumina_scenarios:
            continue
        generator.add_test_result(
            r["nodeid"], r["outcome"], r["duration"],
            r["error"], r.get("requests", [])
        )

    for s in _lumina_scenarios:
        generator.add_scenario_report(s)
        # 将场景中的每个步骤展开为独立的用例明细（含接口请求数据）
        for step in s.get("steps", []):
            generator.add_test_result(
                step["testcase"], step["status"], step.get("duration", 0),
                step.get("error", ""), step.get("requests", [])
            )

    # 生成报告并自动打开
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(__file__).parent / "reports" / "html" / f"LuminaPayroll_Report_{timestamp}.html"
    output = generator.generate(str(report_path))
    session.config._lumina_report_path = output

    import webbrowser
    webbrowser.open(f"file://{output}")


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

@pytest.fixture(scope="session")
def yonyou_session() -> requests.Session:
    """
    从环境变量 YONYOU_COOKIE 构建已认证的 requests.Session，
    并注册请求拦截器用于接口回放。
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

    # 注册请求拦截器
    session.hooks["response"].append(_capture_response)

    print(f"\n[Fixture] 已加载 {len(session.cookies)} 个 cookie")
    return session
