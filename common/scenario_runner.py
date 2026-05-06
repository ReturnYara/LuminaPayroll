"""
场景执行引擎

解析 scenarios/*.yaml，按步骤串联执行原子用例，支持上下文传递。

用法:
    # 直接运行
    python -m common.scenario_runner scenarios/payfile_calculate_flow.yaml

    # 被 pytest 调用（通过 test_scenarios.py）
    pytest testcases/test_scenarios.py -v
"""

import os
import re
import sys
import yaml
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ScenarioContext:
    """场景上下文，用于步骤间传递数据"""

    def __init__(self, global_params: Dict[str, Any] = None):
        self._data = dict(global_params or {})
        self.step_results = []

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def resolve(self, value: str) -> str:
        """解析 ${variable} 占位符"""
        if not isinstance(value, str):
            return value

        def replacer(match):
            var_name = match.group(1)
            return str(self._data.get(var_name, match.group(0)))

        return re.sub(r'\$\{(\w+)\}', replacer, value)

    def resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """解析参数字典中的所有占位符"""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str):
                resolved[key] = self.resolve(value)
            elif isinstance(value, list):
                resolved[key] = [self.resolve(v) if isinstance(v, str) else v for v in value]
            else:
                resolved[key] = value
        return resolved

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class StepResult:
    """单步执行结果"""

    def __init__(self, name: str, testcase: str):
        self.name = name
        self.testcase = testcase
        self.status = "pending"     # pending / passed / failed / skipped
        self.duration = 0.0
        self.output = ""
        self.error = ""
        self.requests = []          # 失败时的接口请求/响应数据

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "testcase": self.testcase,
            "status": self.status,
            "duration": round(self.duration, 2),
            "error": self.error,
            "requests": self.requests
        }


class ScenarioRunner:
    """场景执行引擎"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.logger = logging.getLogger("ScenarioRunner")

    def load_scenario(self, yaml_path: str) -> Dict[str, Any]:
        """加载场景 YAML"""
        path = Path(yaml_path)
        if not path.is_absolute():
            path = self.project_root / path

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def find_scenario_by_name(self, name: str) -> Optional[str]:
        """按名称模糊匹配场景文件"""
        scenarios_dir = self.project_root / "scenarios"
        if not scenarios_dir.exists():
            return None

        best_match = None
        best_score = 0

        for yaml_file in scenarios_dir.glob("*.yaml"):
            scenario = self.load_scenario(str(yaml_file))
            scenario_name = scenario.get("name", "")
            scenario_desc = scenario.get("description", "")
            tags = scenario.get("tags", [])

            # 简单关键词匹配评分
            score = 0
            search_lower = name.lower()
            if search_lower in scenario_name.lower():
                score += 10
            if search_lower in scenario_desc.lower():
                score += 5
            for tag in tags:
                if tag.lower() in search_lower or search_lower in tag.lower():
                    score += 3
            # 逐词匹配
            for word in search_lower.split():
                if word in scenario_name.lower() or word in scenario_desc.lower():
                    score += 2
                for tag in tags:
                    if word in tag.lower():
                        score += 1

            if score > best_score:
                best_score = score
                best_match = str(yaml_file)

        return best_match if best_score > 0 else None

    def run_scenario(self, yaml_path: str) -> Dict[str, Any]:
        """执行场景
        
        支持 critical / depends_on 字段：
        - critical: true（默认）表示关键步骤，影响场景最终结果
        - critical: false 非关键步骤，失败不影响场景最终判定
        - depends_on: 依赖的步骤名称列表，被依赖步骤失败则本步骤跳过
        
        参数加载优先级（高→低）：
        1. 步骤级 params
        2. global_params_override（场景 YAML 中的临时覆盖）
        3. data_file 引用的数据文件（单一数据源）
        4. global_params（兼容旧格式）
        """
        scenario = self.load_scenario(yaml_path)

        name = scenario.get("name", "未命名场景")
        steps = scenario.get("steps", [])

        # 加载全局参数：优先从 data_file 读取，再合并 global_params 和 override
        global_params = {}

        # 1. 从 data_file 加载（单一数据源）
        data_file = scenario.get("data_file")
        if data_file:
            data_path = self.project_root / data_file
            if data_path.exists():
                with open(data_path, "r", encoding="utf-8") as f:
                    global_params = yaml.safe_load(f) or {}
                self.logger.info(f"已从 {data_file} 加载 {len(global_params)} 个参数")
            else:
                self.logger.warning(f"数据文件不存在: {data_path}")

        # 2. 兼容旧格式 global_params（如果有）
        legacy_params = scenario.get("global_params", {})
        if legacy_params:
            global_params.update(legacy_params)

        # 3. 合并 override（优先级最高）
        override = scenario.get("global_params_override", {})
        if override:
            global_params.update(override)

        self.logger.info(f"========== 场景: {name} ==========")
        self.logger.info(f"共 {len(steps)} 个步骤")

        context = ScenarioContext(global_params)
        results = []
        # 记录每个步骤名称 → 执行状态，供 depends_on 查询
        step_status_map: Dict[str, str] = {}

        for i, step in enumerate(steps, 1):
            step_name = step.get("name", f"步骤{i}")
            testcase = step.get("testcase", "")
            params = step.get("params", {})
            save_to = step.get("save_to_context", {})
            use_from = step.get("use_from_context", {})
            is_critical = step.get("critical", True)
            depends_on = step.get("depends_on", [])

            self.logger.info(f"\n--- 步骤 {i}/{len(steps)}: {step_name} "
                             f"{'[关键]' if is_critical else '[非关键]'} ---")

            # 检查依赖步骤是否通过
            dep_failed = [dep for dep in depends_on
                          if step_status_map.get(dep) in ("failed", "skipped")]
            if dep_failed:
                skip_result = StepResult(step_name, testcase)
                skip_result.status = "skipped"
                skip_result.error = f"依赖步骤未通过: {', '.join(dep_failed)}"
                results.append(skip_result)
                step_status_map[step_name] = "skipped"
                self.logger.info(f"跳过: 依赖步骤 {dep_failed} 未通过")
                continue

            # 从上下文读取参数
            for param_key, context_key in use_from.items():
                params[param_key] = context.get(context_key, "")

            # 解析占位符
            resolved_params = context.resolve_params(params)

            # 执行
            result = self._run_step(testcase, resolved_params)
            result.name = step_name
            results.append(result)
            step_status_map[step_name] = result.status

            # 保存到上下文
            for context_key, json_path in save_to.items():
                context.set(context_key, json_path)

            if result.status == "failed":
                if is_critical:
                    self.logger.error(f"关键步骤失败: {step_name}")
                else:
                    self.logger.warning(f"非关键步骤失败: {step_name}（不影响后续执行）")
            else:
                self.logger.info(f"步骤通过: {step_name} ({result.duration:.1f}s)")

        # 汇总 —— 场景是否通过仅由关键步骤决定
        critical_steps = [(step, r) for step, r in zip(steps, results)
                          if step.get("critical", True)]
        critical_failed = sum(1 for _, r in critical_steps if r.status == "failed")
        all_passed = critical_failed == 0

        report = {
            "scenario": name,
            "status": "passed" if all_passed else "failed",
            "timestamp": datetime.now().isoformat(),
            "steps": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.status == "passed"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "skipped": sum(1 for r in results if r.status == "skipped"),
                "critical_failed": critical_failed
            }
        }

        self.logger.info(f"\n========== 场景结束: {report['status'].upper()} ==========")
        self.logger.info(f"通过: {report['summary']['passed']}, "
                         f"失败: {report['summary']['failed']}, "
                         f"跳过: {report['summary']['skipped']}, "
                         f"关键失败: {critical_failed}")

        return report

    def _run_step(self, testcase: str, params: Dict[str, Any]) -> StepResult:
        """执行单个步骤（调用 pytest 运行对应原子用例）"""
        result = StepResult("", testcase)
        start = datetime.now()

        # 构建 pytest 命令
        cmd = [
            sys.executable, "-m", "pytest",
            testcase,
            "-v",
            "--tb=short",
            "--no-header",
            "-q"
        ]

        # 准备请求日志临时文件路径
        import tempfile
        request_log_fd, request_log_path = tempfile.mkstemp(
            prefix="lumina_req_", suffix=".json", dir=str(self.project_root / "reports")
        )
        os.close(request_log_fd)

        # 通过环境变量把参数传给原子用例
        env = os.environ.copy()
        env["LUMINA_SUBPROCESS"] = "1"
        env["LUMINA_REQUEST_LOG_PATH"] = request_log_path
        for key, value in params.items():
            env[f"SCENARIO_PARAM_{key.upper()}"] = str(value)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )

            result.output = proc.stdout
            result.error = proc.stderr
            result.status = "passed" if proc.returncode == 0 else "failed"

        except subprocess.TimeoutExpired:
            result.status = "failed"
            result.error = "执行超时(300s)"
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = (datetime.now() - start).total_seconds()

        # 读取子进程写入的请求日志（仅失败时有数据）
        try:
            if os.path.exists(request_log_path) and os.path.getsize(request_log_path) > 0:
                with open(request_log_path, "r", encoding="utf-8") as f:
                    result.requests = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        finally:
            # 清理临时文件
            try:
                os.unlink(request_log_path)
            except OSError:
                pass

        return result


def list_scenarios(project_root: str = None) -> List[Dict[str, Any]]:
    """列出所有可用场景"""
    runner = ScenarioRunner(project_root)
    scenarios_dir = runner.project_root / "scenarios"
    result = []

    if not scenarios_dir.exists():
        return result

    for yaml_file in sorted(scenarios_dir.glob("*.yaml")):
        scenario = runner.load_scenario(str(yaml_file))
        result.append({
            "file": str(yaml_file.relative_to(runner.project_root)),
            "name": scenario.get("name", ""),
            "description": scenario.get("description", ""),
            "tags": scenario.get("tags", []),
            "steps_count": len(scenario.get("steps", []))
        })

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m common.scenario_runner <场景YAML路径>")
        print("  python -m common.scenario_runner --list")
        print("  python -m common.scenario_runner --find '计算薪资'")
        sys.exit(1)

    if sys.argv[1] == "--list":
        for s in list_scenarios():
            print(f"  [{', '.join(s['tags'])}] {s['name']} ({s['steps_count']}步) - {s['file']}")
        sys.exit(0)

    if sys.argv[1] == "--find":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        runner = ScenarioRunner()
        match = runner.find_scenario_by_name(query)
        if match:
            print(f"匹配到: {match}")
        else:
            print("未找到匹配的场景")
        sys.exit(0)

    runner = ScenarioRunner()
    report = runner.run_scenario(sys.argv[1])

    # 保存报告
    report_path = Path("reports") / f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {report_path}")
    sys.exit(0 if report["status"] == "passed" else 1)
