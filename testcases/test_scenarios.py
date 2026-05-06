"""
场景层测试入口

将 scenarios/*.yaml 中的每个场景自动生成为一个 pytest 用例。
运行方式:
    pytest testcases/test_scenarios.py -v                          # 跑所有场景
    pytest testcases/test_scenarios.py -v -k "计算"                 # 按名称筛选
    pytest testcases/test_scenarios.py -v --scenario=场景文件.yaml   # 指定场景文件
"""

import os
import pytest
from pathlib import Path
from common.scenario_runner import ScenarioRunner, list_scenarios


# 收集所有场景 YAML
PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"


def get_all_scenarios():
    """收集所有场景文件，供 parametrize 使用"""
    if not SCENARIOS_DIR.exists():
        return []

    scenarios = []
    for yaml_file in sorted(SCENARIOS_DIR.glob("*.yaml")):
        import yaml
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        name = data.get("name", yaml_file.stem)
        scenarios.append(pytest.param(str(yaml_file), id=name))

    return scenarios


class TestScenarios:
    """场景层测试"""

    @pytest.mark.parametrize("scenario_path", get_all_scenarios())
    def test_scenario(self, scenario_path):
        """场景用例：发放单基础算税"""
        runner = ScenarioRunner(str(PROJECT_ROOT))
        report = runner.run_scenario(scenario_path)

        # 加载场景描述信息
        import yaml
        with open(scenario_path, "r", encoding="utf-8") as f:
            scenario_meta = yaml.safe_load(f)
        report["description"] = scenario_meta.get("description", "")

        # 注册到全局报告收集器
        import conftest as _conftest
        _conftest._lumina_scenarios.append(report)

        # 打印步骤结果
        for step in report["steps"]:
            status_icon = {"passed": "OK", "failed": "FAIL", "skipped": "SKIP"}.get(step["status"], "?")
            print(f"  [{status_icon}] {step['name']} ({step['duration']}s)")
            if step["error"]:
                print(f"       {step['error'][:200]}")

        # 断言场景整体通过（仅关键步骤失败才判定场景失败）
        summary = report["summary"]
        assert report["status"] == "passed", (
            f"场景失败: {summary.get('critical_failed', summary['failed'])} 个关键步骤失败, "
            f"{summary['failed']} 个步骤失败, "
            f"{summary['skipped']} 个步骤跳过"
        )
