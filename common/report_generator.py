"""
LuminaPayroll 自定义测试报告生成器

生成扁平化风格的 HTML 测试报告，包含：
- 数据看板（总数/通过/失败/跳过/耗时）
- 场景概览（场景名称、简介、状态）
- 用例明细（成功/失败/跳过 三页签）
- 失败用例接口回放按钮
"""

import json
import html as html_escape
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path


class ReportGenerator:
    """自定义 HTML 报告生成器"""

    TEST_DESCRIPTIONS = {
        "test_scenario": "场景用例：发放单基础算税",
        "test_verify_calculate_success": "验证计算状态",
        "test_verify_calculate_with_selected_docs": "验证默认计算全部人员",
        "test_calcalute_success": "验证计算状态",
        "test_calcalute_without_verify_should_still_work": "验证计算接口的独立性",
        "test_query_details_after_calculate_success": "验证发放单计算结果",
        "test_specified_sum_without_approve": "验证未审批时指定期间合计数",
        "test_specified_avg_without_approve": "验证未审批时指定期间平均数",
        "test_emp_info_obtain": "验证获取员工信息集",
        "test_taxpayer_info_obtain": "验证获取纳税人员信息集",
        "test_Standard_Deduction": "验证获取减除费用扣除信息集",
    }

    def __init__(self):
        self.scenarios: List[Dict[str, Any]] = []
        self.test_results: List[Dict[str, Any]] = []
        self.start_time: datetime = None
        self.end_time: datetime = None

    def set_timing(self, start: datetime, end: datetime):
        self.start_time = start
        self.end_time = end

    def add_scenario_report(self, report: Dict[str, Any]):
        self.scenarios.append(report)

    def add_test_result(self, nodeid: str, outcome: str, duration: float,
                        error: str = "", requests_data: List[Dict] = None):
        self.test_results.append({
            "nodeid": nodeid,
            "outcome": outcome,
            "duration": round(duration, 2),
            "error": error,
            "requests": requests_data or []
        })

    @classmethod
    def get_test_description(cls, nodeid: str) -> str:
        for key, desc in cls.TEST_DESCRIPTIONS.items():
            if key in nodeid:
                return desc
        return nodeid

    def generate(self, output_path: str) -> str:
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["outcome"] == "passed")
        failed = sum(1 for r in self.test_results if r["outcome"] == "failed")
        skipped = sum(1 for r in self.test_results if r["outcome"] == "skipped")
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0

        report_data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": round(duration, 2),
            "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
            "scenarios": self.scenarios,
            "test_results": self.test_results
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(self._render_html(report_data))
        return str(output)

    def _render_html(self, data: Dict[str, Any]) -> str:
        summary = data["summary"]
        pass_rate = round(summary["passed"] / summary["total"] * 100, 1) if summary["total"] > 0 else 0
        fail_pct = round(summary["failed"] / summary["total"] * 100, 1) if summary["total"] > 0 else 0
        skip_pct = round(summary["skipped"] / summary["total"] * 100, 1) if summary["total"] > 0 else 0

        scenarios_html = self._render_scenarios(data["scenarios"])

        passed_list = [r for r in data["test_results"] if r["outcome"] == "passed"]
        failed_list = [r for r in data["test_results"] if r["outcome"] == "failed"]
        skipped_list = [r for r in data["test_results"] if r["outcome"] == "skipped"]

        tab_passed = self._render_test_items(passed_list, "passed")
        tab_failed = self._render_test_items(failed_list, "failed")
        tab_skipped = self._render_test_items(skipped_list, "skipped")

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>发放单计算场景自动化测试报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #f5f7fa;
    color: #2c3e50;
    line-height: 1.6;
    padding: 24px;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
.header {{
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 32px; padding-bottom: 16px; border-bottom: 2px solid #e8ecf0;
}}
.header h1 {{ font-size: 24px; font-weight: 600; color: #1a2332; }}
.header .meta {{ font-size: 14px; color: #7f8c9b; text-align: right; }}

.dashboard {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px; margin-bottom: 32px;
}}
.card {{
    background: #fff; border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: transform 0.2s;
}}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
.card .label {{ font-size: 13px; color: #7f8c9b; letter-spacing: 0.5px; margin-bottom: 8px; }}
.card .value {{ font-size: 32px; font-weight: 700; }}
.card.total .value {{ color: #2c3e50; }}
.card.passed .value {{ color: #27ae60; }}
.card.failed .value {{ color: #e74c3c; }}
.card.skipped .value {{ color: #f39c12; }}
.card.duration .value {{ color: #3498db; font-size: 28px; }}
.card.rate .value {{ color: #8e44ad; }}

.progress-bar {{
    margin-bottom: 32px; background: #e8ecf0; border-radius: 8px;
    height: 8px; overflow: hidden; display: flex;
}}
.progress-bar .seg-passed {{ background: #27ae60; }}
.progress-bar .seg-failed {{ background: #e74c3c; }}
.progress-bar .seg-skipped {{ background: #f39c12; }}

.section {{ margin-bottom: 32px; }}
.section-title {{
    font-size: 18px; font-weight: 600; color: #1a2332;
    margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
}}
.section-title::before {{
    content: ''; width: 4px; height: 20px; background: #3498db; border-radius: 2px;
}}

.scenario-card {{
    background: #fff; border-radius: 12px; padding: 24px;
    margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.scenario-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }}
.scenario-name {{ font-size: 16px; font-weight: 600; color: #1a2332; }}
.scenario-desc {{ font-size: 14px; color: #7f8c9b; margin-bottom: 16px; }}

.badge {{
    display: inline-flex; align-items: center; padding: 4px 12px;
    border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;
}}
.badge.passed {{ background: #d4efdf; color: #27ae60; }}
.badge.failed {{ background: #fadbd8; color: #e74c3c; }}
.badge.skipped {{ background: #fef5e7; color: #f39c12; }}

.steps-table {{ width: 100%; border-collapse: collapse; }}
.steps-table th {{
    text-align: left; padding: 10px 12px; font-size: 12px; color: #7f8c9b;
    letter-spacing: 0.5px; border-bottom: 1px solid #e8ecf0;
}}
.steps-table td {{ padding: 12px; font-size: 14px; border-bottom: 1px solid #f0f2f5; }}
.steps-table tr:last-child td {{ border-bottom: none; }}
.steps-table .step-name {{ font-weight: 500; }}
.steps-table .step-duration {{ color: #7f8c9b; font-variant-numeric: tabular-nums; }}
.steps-table .step-error {{ font-size: 12px; color: #e74c3c; margin-top: 4px; }}

.status-dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px;
}}
.status-dot.passed {{ background: #27ae60; }}
.status-dot.failed {{ background: #e74c3c; }}
.status-dot.skipped {{ background: #f39c12; }}

/* 页签 */
.tabs {{
    background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); overflow: hidden;
}}
.tab-nav {{
    display: flex; border-bottom: 1px solid #e8ecf0; padding: 0 8px;
}}
.tab-btn {{
    padding: 14px 24px; font-size: 14px; font-weight: 500; color: #7f8c9b;
    background: none; border: none; cursor: pointer; position: relative;
    transition: color 0.2s;
}}
.tab-btn:hover {{ color: #2c3e50; }}
.tab-btn.active {{ color: #3498db; }}
.tab-btn.active::after {{
    content: ''; position: absolute; bottom: -1px; left: 12px; right: 12px;
    height: 2px; background: #3498db; border-radius: 1px;
}}
.tab-btn .count {{
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 20px; height: 20px; padding: 0 6px;
    border-radius: 10px; font-size: 11px; font-weight: 600; margin-left: 6px;
}}
.tab-btn .count.c-passed {{ background: #d4efdf; color: #27ae60; }}
.tab-btn .count.c-failed {{ background: #fadbd8; color: #e74c3c; }}
.tab-btn .count.c-skipped {{ background: #fef5e7; color: #f39c12; }}

.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}

.test-item {{
    display: flex; align-items: center; padding: 14px 20px;
    border-bottom: 1px solid #f0f2f5; gap: 12px;
}}
.test-item:last-child {{ border-bottom: none; }}
.test-item .test-desc {{ flex: 1; font-size: 14px; color: #2c3e50; font-weight: 500; }}
.test-item .test-duration {{
    font-size: 13px; color: #7f8c9b; font-variant-numeric: tabular-nums;
    min-width: 60px; text-align: right;
}}

/* 回放按钮 */
.replay-btn {{
    padding: 4px 12px; font-size: 12px; font-weight: 500; color: #3498db;
    background: #eaf2fb; border: 1px solid #c8ddf2; border-radius: 6px;
    cursor: pointer; transition: all 0.2s; white-space: nowrap;
}}
.replay-btn:hover {{ background: #d4e6f9; border-color: #3498db; }}

.replay-panel {{
    display: none; margin: 0 20px 12px 36px; padding: 16px;
    background: #f8f9fb; border-radius: 8px; border: 1px solid #e8ecf0;
}}
.replay-panel.open {{ display: block; }}
.replay-panel .req-block {{
    margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px dashed #e0e4e8;
}}
.replay-panel .req-block:last-child {{ margin-bottom: 0; border-bottom: none; }}
.replay-panel .req-label {{
    font-size: 12px; font-weight: 600; color: #7f8c9b; margin-bottom: 4px;
}}
.replay-panel .req-url {{
    font-size: 13px; font-family: 'SF Mono', Menlo, monospace; color: #2c3e50;
    word-break: break-all; margin-bottom: 8px;
}}
.replay-panel .method-tag {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 11px; font-weight: 700; margin-right: 6px; color: #fff;
}}
.method-tag.POST {{ background: #27ae60; }}
.method-tag.GET {{ background: #3498db; }}
.method-tag.PUT {{ background: #f39c12; }}
.method-tag.DELETE {{ background: #e74c3c; }}
.replay-panel pre {{
    background: #1a2332; color: #e8ecf0; padding: 12px 16px;
    border-radius: 6px; font-size: 12px; line-height: 1.5;
    overflow-x: auto; white-space: pre-wrap; word-break: break-all;
    max-height: 300px;
}}
.replay-panel .status-code {{
    font-size: 12px; font-weight: 600; margin-left: 8px;
}}
.replay-panel .status-code.ok {{ color: #27ae60; }}
.replay-panel .status-code.err {{ color: #e74c3c; }}

.empty-tip {{
    padding: 40px 20px; text-align: center; color: #7f8c9b; font-size: 14px;
}}

/* 图表 */
.charts-container {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;
}}
.chart-card {{
    background: #fff; border-radius: 12px; padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.chart-title {{
    font-size: 14px; font-weight: 600; color: #1a2332; margin-bottom: 16px;
}}
.chart-body {{
    display: flex; align-items: center; justify-content: center; min-height: 160px;
}}
.chart-body.pie-body {{
    flex-direction: column; gap: 16px;
}}
.chart-legend {{
    display: flex; gap: 20px; justify-content: center;
}}
.legend-item {{
    display: flex; align-items: center; gap: 6px; font-size: 13px; color: #2c3e50;
}}
.legend-dot {{
    width: 10px; height: 10px; border-radius: 50%; display: inline-block;
}}

.footer {{
    text-align: center; margin-top: 32px; font-size: 13px; color: #7f8c9b;
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>发放单计算场景自动化测试报告</h1>
        <div class="meta">
            <div>生成时间：{data['generated_at']}</div>
            <div>总耗时：{data['duration']}s</div>
        </div>
    </div>

    <div class="dashboard">
        <div class="card total"><div class="label">用例总数</div><div class="value">{summary['total']}</div></div>
        <div class="card passed"><div class="label">通过</div><div class="value">{summary['passed']}</div></div>
        <div class="card failed"><div class="label">失败</div><div class="value">{summary['failed']}</div></div>
        <div class="card skipped"><div class="label">跳过</div><div class="value">{summary['skipped']}</div></div>
        <div class="card duration"><div class="label">执行耗时</div><div class="value">{data['duration']}s</div></div>
        <div class="card rate"><div class="label">通过率</div><div class="value">{pass_rate}%</div></div>
    </div>

    <div class="progress-bar">
        <div class="seg-passed" style="width:{pass_rate}%"></div>
        <div class="seg-failed" style="width:{fail_pct}%"></div>
        <div class="seg-skipped" style="width:{skip_pct}%"></div>
    </div>

    {scenarios_html}

    <div class="section">
        <div class="section-title">用例明细</div>
        <div class="tabs">
            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab(event,'tab-passed')">
                    通过<span class="count c-passed">{summary['passed']}</span>
                </button>
                <button class="tab-btn" onclick="switchTab(event,'tab-failed')">
                    失败<span class="count c-failed">{summary['failed']}</span>
                </button>
                <button class="tab-btn" onclick="switchTab(event,'tab-skipped')">
                    跳过<span class="count c-skipped">{summary['skipped']}</span>
                </button>
            </div>
            <div id="tab-passed" class="tab-panel active">{tab_passed}</div>
            <div id="tab-failed" class="tab-panel">{tab_failed}</div>
            <div id="tab-skipped" class="tab-panel">{tab_skipped}</div>
        </div>
    </div>

    <div class="footer">LuminaPayroll Automation Report</div>
</div>

<script>
function switchTab(e, panelId) {{
    var container = e.currentTarget.closest('.tabs');
    container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    e.currentTarget.classList.add('active');
    document.getElementById(panelId).classList.add('active');
}}
function toggleReplay(id) {{
    var el = document.getElementById(id);
    el.classList.toggle('open');
}}
</script>
</body>
</html>"""

    def _render_scenarios(self, scenarios: List[Dict[str, Any]]) -> str:
        if not scenarios:
            return ""

        # 按场景名称中的数字排序（场景一、场景二、场景三）
        import re
        cn_num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                      "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

        def sort_key(s):
            name = s.get("scenario", "")
            for cn, num in cn_num_map.items():
                if cn in name:
                    return num
            # fallback: 按数字提取
            m = re.search(r'\d+', name)
            return int(m.group()) if m else 99

        sorted_scenarios = sorted(scenarios, key=sort_key)

        html = '<div class="section"><div class="section-title">场景执行概览</div>'

        # 渲染图表区域
        html += self._render_charts(sorted_scenarios)

        # 渲染场景页签
        tab_nav = '<div class="tab-nav">'
        tab_panels = ""

        for idx, scenario in enumerate(sorted_scenarios):
            name = scenario.get("scenario", "未命名")
            short_name = name.split("：")[0] if "：" in name else name[:6]
            desc = scenario.get("description", "")
            status = scenario.get("status", "unknown")
            steps = scenario.get("steps", [])

            active_cls = " active" if idx == 0 else ""
            panel_id = f"scenario-{idx}"

            # 页签按钮：根据场景状态设置颜色
            count_cls = "c-passed" if status == "passed" else "c-failed"
            tab_nav += f'<button class="tab-btn{active_cls}" onclick="switchTab(event,\'{panel_id}\')">{short_name}<span class="count {count_cls}">{len(steps)}</span></button>'

            # 页签面板：场景卡片
            steps_rows = ""
            for step in steps:
                s = step.get("status", "unknown")
                testcase = step.get("testcase", "")
                step_desc = self.get_test_description(testcase)
                err = ""
                if step.get("error"):
                    err = f'<div class="step-error">{html_escape.escape(step["error"][:200])}</div>'

                steps_rows += f"""<tr>
                    <td><span class="status-dot {s}"></span><span class="step-name">{step_desc}</span>{err}</td>
                    <td><span class="badge {s}">{s}</span></td>
                    <td class="step-duration">{step.get('duration', 0)}s</td>
                </tr>"""

            tab_panels += f"""<div id="{panel_id}" class="tab-panel{active_cls}">
                <div class="scenario-card" style="margin-bottom:0;box-shadow:none;">
                    <div class="scenario-header">
                        <span class="scenario-name">{name}</span>
                        <span class="badge {status}">{status}</span>
                    </div>
                    <div class="scenario-desc">{desc}</div>
                    <table class="steps-table">
                        <thead><tr><th>步骤</th><th>状态</th><th>耗时</th></tr></thead>
                        <tbody>{steps_rows}</tbody>
                    </table>
                </div>
            </div>"""

        tab_nav += '</div>'
        html += f'<div class="tabs">{tab_nav}{tab_panels}</div>'
        html += "</div>"
        return html

    def _render_charts(self, scenarios: List[Dict[str, Any]]) -> str:
        """渲染柱状图（各场景用例分布）和饼图（成功/失败占比）"""
        # 统计每个场景的通过/失败/跳过
        chart_data = []
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for s in scenarios:
            name = s.get("scenario", "未命名")
            # 取简短名（场景一/二/三）
            short_name = name.split("：")[0] if "：" in name else name[:6]
            steps = s.get("steps", [])
            p = sum(1 for st in steps if st.get("status") == "passed")
            f_ = sum(1 for st in steps if st.get("status") == "failed")
            sk = sum(1 for st in steps if st.get("status") == "skipped")
            chart_data.append({"name": short_name, "passed": p, "failed": f_, "skipped": sk, "total": p + f_ + sk})
            total_passed += p
            total_failed += f_
            total_skipped += sk

        grand_total = total_passed + total_failed + total_skipped
        if grand_total == 0:
            return ""

        # === 柱状图 SVG（左右并列：绿色通过 + 红色失败）===
        sub_bar_width = 24
        group_width = sub_bar_width * 2 + 8  # 两根柱子 + 间隙
        group_gap = 50
        chart_width = len(chart_data) * (group_width + group_gap) + 80
        chart_height = 200
        max_count = max(max(d["passed"], d["failed"]) for d in chart_data) if chart_data else 1
        if max_count == 0:
            max_count = 1
        scale = 130 / max_count

        bars_svg = ""
        for i, d in enumerate(chart_data):
            gx = 50 + i * (group_width + group_gap)
            y_base = chart_height - 35

            # 左：通过(绿)
            h_p = d["passed"] * scale
            bars_svg += f'<rect x="{gx}" y="{y_base - h_p}" width="{sub_bar_width}" height="{h_p}" fill="#27ae60" rx="3"/>'
            if d["passed"] > 0:
                bars_svg += f'<text x="{gx + sub_bar_width/2}" y="{y_base - h_p - 6}" text-anchor="middle" font-size="11" fill="#27ae60" font-weight="600">{d["passed"]}</text>'

            # 右：失败(红)
            rx = gx + sub_bar_width + 8
            h_f = d["failed"] * scale
            bars_svg += f'<rect x="{rx}" y="{y_base - h_f}" width="{sub_bar_width}" height="{h_f}" fill="#e74c3c" rx="3"/>'
            if d["failed"] > 0:
                bars_svg += f'<text x="{rx + sub_bar_width/2}" y="{y_base - h_f - 6}" text-anchor="middle" font-size="11" fill="#e74c3c" font-weight="600">{d["failed"]}</text>'

            # 场景名称
            bars_svg += f'<text x="{gx + group_width/2}" y="{y_base + 18}" text-anchor="middle" font-size="12" fill="#7f8c9b">{d["name"]}</text>'

        # 图例
        legend_y = 14
        bars_svg += f'<rect x="{chart_width - 130}" y="{legend_y - 8}" width="10" height="10" fill="#27ae60" rx="2"/>'
        bars_svg += f'<text x="{chart_width - 116}" y="{legend_y}" font-size="11" fill="#7f8c9b">通过</text>'
        bars_svg += f'<rect x="{chart_width - 80}" y="{legend_y - 8}" width="10" height="10" fill="#e74c3c" rx="2"/>'
        bars_svg += f'<text x="{chart_width - 66}" y="{legend_y}" font-size="11" fill="#7f8c9b">失败</text>'

        bar_chart = f"""<svg width="{chart_width}" height="{chart_height}" viewBox="0 0 {chart_width} {chart_height}">
            {bars_svg}
        </svg>"""

        # === 饼图 SVG (Conic gradient 模拟) ===
        import math
        pie_size = 160
        cx, cy, r = pie_size / 2, pie_size / 2, 60

        def arc_path(start_angle, end_angle, color):
            if end_angle - start_angle >= 360:
                # 整圆
                return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
            start_rad = math.radians(start_angle - 90)
            end_rad = math.radians(end_angle - 90)
            x1 = cx + r * math.cos(start_rad)
            y1 = cy + r * math.sin(start_rad)
            x2 = cx + r * math.cos(end_rad)
            y2 = cy + r * math.sin(end_rad)
            large_arc = 1 if (end_angle - start_angle) > 180 else 0
            return f'<path d="M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large_arc} 1 {x2} {y2} Z" fill="{color}"/>'

        passed_angle = (total_passed / grand_total) * 360
        failed_angle = (total_failed / grand_total) * 360

        pie_paths = ""
        if total_passed == grand_total:
            pie_paths = arc_path(0, 360, "#27ae60")
        elif total_failed == grand_total:
            pie_paths = arc_path(0, 360, "#e74c3c")
        else:
            angle = 0
            if total_passed > 0:
                pie_paths += arc_path(angle, angle + passed_angle, "#27ae60")
                angle += passed_angle
            if total_failed > 0:
                pie_paths += arc_path(angle, angle + failed_angle, "#e74c3c")
                angle += failed_angle
            if total_skipped > 0:
                pie_paths += arc_path(angle, angle + (360 - passed_angle - failed_angle), "#f39c12")

        pass_pct = round(total_passed / grand_total * 100, 1)
        fail_pct = round(total_failed / grand_total * 100, 1)
        skip_pct = round(total_skipped / grand_total * 100, 1)

        pie_chart = f"""<svg width="{pie_size}" height="{pie_size}" viewBox="0 0 {pie_size} {pie_size}">
            {pie_paths}
            <circle cx="{cx}" cy="{cy}" r="35" fill="#fff"/>
            <text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="16" font-weight="700" fill="#2c3e50">{pass_pct}%</text>
        </svg>"""

        legend = f"""<div class="chart-legend">
            <div class="legend-item"><span class="legend-dot" style="background:#27ae60"></span>通过 {total_passed} ({pass_pct}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background:#e74c3c"></span>失败 {total_failed} ({fail_pct}%)</div>
            <div class="legend-item"><span class="legend-dot" style="background:#f39c12"></span>跳过 {total_skipped} ({skip_pct}%)</div>
        </div>"""

        return f"""<div class="charts-container">
            <div class="chart-card">
                <div class="chart-title">各场景用例分布</div>
                <div class="chart-body">{bar_chart}</div>
            </div>
            <div class="chart-card">
                <div class="chart-title">用例通过率</div>
                <div class="chart-body pie-body">{pie_chart}{legend}</div>
            </div>
        </div>"""

    def _render_test_items(self, results: List[Dict[str, Any]], category: str) -> str:
        if not results:
            return '<div class="empty-tip">暂无数据</div>'

        items = ""
        for idx, r in enumerate(results):
            desc = self.get_test_description(r["nodeid"])
            replay_btn = ""
            replay_panel = ""

            # 失败用例：渲染接口回放按钮（按钮在行内，面板在行外展开）
            if category == "failed" and r.get("requests"):
                panel_id = f"replay-{category}-{idx}"
                replay_btn = f'<button class="replay-btn" onclick="toggleReplay(\'{panel_id}\')">接口回放</button>'

                req_blocks = ""
                for i, req in enumerate(r["requests"]):
                    method = req.get("method", "GET")
                    url = html_escape.escape(req.get("url", ""))
                    body = html_escape.escape(req.get("request_body", "")) or "（无请求体）"
                    resp = html_escape.escape(req.get("response_body", ""))
                    sc = req.get("status_code", 0)
                    sc_cls = "ok" if 200 <= sc < 300 else "err"

                    req_blocks += f"""<div class="req-block">
                        <div class="req-label">请求 {i+1}</div>
                        <div class="req-url"><span class="method-tag {method}">{method}</span>{url}
                            <span class="status-code {sc_cls}">HTTP {sc}</span>
                        </div>
                        <div class="req-label">Request Body</div>
                        <pre>{body}</pre>
                        <div class="req-label" style="margin-top:8px">Response Body</div>
                        <pre>{resp}</pre>
                    </div>"""

                replay_panel = f'<div id="{panel_id}" class="replay-panel">{req_blocks}</div>'

            # 失败用例显示错误摘要
            error_html = ""
            if category == "failed" and r.get("error"):
                error_html = f'<div class="step-error" style="padding:0 20px 8px 36px;font-size:12px;color:#e74c3c;">{html_escape.escape(r["error"][:200])}</div>'

            items += f"""<div class="test-item">
                <span class="status-dot {r['outcome']}"></span>
                <span class="test-desc">{desc}</span>
                <span class="test-duration">{r['duration']}s</span>
                <span class="badge {r['outcome']}">{r['outcome']}</span>
                {replay_btn}
            </div>
            {error_html}
            {replay_panel}"""

        return items
