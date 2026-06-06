"""数据预置总调度器

串联 6 个预置步骤，按顺序执行：
1. 公共薪资项目创建
2. 发薪方案创建
3. 发薪人员匹配
4. 纳税人员同步并报送
5. 专项附加扣除下载
6. 新建发放单并计算

每步都有幂等检查，已有数据则跳过。
最终输出所有步骤产生的关键数据（ID等）供后续测试使用。

使用说明：
    export YONYOU_COOKIE="..."
    export YONYOU_XSRF_TOKEN="..."
    cd LuminaPayroll
    python3 preset/preset_runner.py
"""

import os
import sys
import json
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preset.preset_utils import create_authenticated_session
from pages.api.salary_item_api import SalaryItemApi
from pages.api.salary_scheme_api import SalarySchemeApi
from pages.api.salary_staff_api import SalaryStaffApi
from pages.api.tax_person_api import TaxPersonApi
from pages.api.special_deduction_api import SpecialDeductionApi
from pages.api.pay_doc_api import PayDocApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class PresetRunner:
    """数据预置总调度器

    协调 6 个步骤的执行，维护步骤间的数据传递。
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Args:
            config: 预置配置，包含方案名、期间等业务参数
        """
        self.config = config or self._load_default_config()
        self.base_url = self.config.get("base_url",
                                        os.getenv("LUMINA_BASE_URL", "https://c4.yonyoucloud.com"))
        self.org_id = self.config.get("org_id", "666666")

        # 创建认证 Session（所有 API 共用）
        self.session = create_authenticated_session()
        self.xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")

        # 步骤间传递的数据
        self.context = {
            "scheme_id": None,
            "scheme_name": None,
            "pay_file_id": None,
            "query_id_str": None,
            "staff_count": 0,
        }

        # 执行结果
        self.results = {
            "start_time": None,
            "end_time": None,
            "steps": {}
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认预置配置"""
        config_path = Path(__file__).parent / "data" / "preset_config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _init_api(self, api_class):
        """初始化 API 实例（注入公共参数）"""
        api = api_class(base_url=self.base_url, session=self.session, org_id=self.org_id)
        if self.xsrf_token:
            api.set_xsrf_token(self.xsrf_token)
        return api

    def run(self, steps: list = None) -> Dict[str, Any]:
        """执行预置流程

        Args:
            steps: 要执行的步骤列表（1-6），默认全部执行

        Returns:
            执行结果
        """
        steps = steps or [1, 2, 3, 4, 5, 6]
        self.results["start_time"] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("  LuminaPayroll 数据预置开始")
        logger.info(f"  环境: {self.base_url}")
        logger.info(f"  组织: {self.org_id}")
        logger.info(f"  步骤: {steps}")
        logger.info("=" * 60)

        step_handlers = {
            1: ("公共薪资项目创建", self._step1_salary_items),
            2: ("发薪方案创建", self._step2_salary_scheme),
            3: ("发薪人员匹配", self._step3_match_staff),
            4: ("纳税人员同步并报送", self._step4_tax_person),
            5: ("专项附加扣除下载", self._step5_special_deduction),
            6: ("新建发放单并计算", self._step6_pay_doc),
        }

        for step_num in steps:
            if step_num not in step_handlers:
                logger.warning(f"未知步骤: {step_num}, 跳过")
                continue

            step_name, handler = step_handlers[step_num]
            logger.info(f"\n{'─'*50}")
            logger.info(f"  步骤 {step_num}: {step_name}")
            logger.info(f"{'─'*50}")

            try:
                result = handler()
                self.results["steps"][step_num] = {
                    "name": step_name,
                    "status": "success",
                    "result": result
                }
                logger.info(f"  ✓ 步骤 {step_num} 完成")
            except Exception as e:
                self.results["steps"][step_num] = {
                    "name": step_name,
                    "status": "failed",
                    "error": str(e)
                }
                logger.error(f"  ✗ 步骤 {step_num} 失败: {e}")
                # 步骤失败后是否继续执行后续步骤
                if self.config.get("stop_on_failure", True):
                    logger.error("  配置为失败即停止，终止后续步骤")
                    break

        self.results["end_time"] = datetime.now().isoformat()
        self._save_results()
        self._print_summary()

        return self.results

    # ==================== 步骤 1：公共薪资项目创建 ====================

    def _step1_salary_items(self) -> Dict:
        """批量创建公共薪资项目"""
        from preset.preset_salary_items import SalaryItemPreset

        preset = SalaryItemPreset(base_url=self.base_url, org_id=self.org_id)
        # 复用已有 session
        preset.api.session = self.session
        if self.xsrf_token:
            preset.api.set_xsrf_token(self.xsrf_token)

        result = preset.run()

        return {
            "created": len(result["created"]),
            "skipped": len(result["skipped"]),
            "failed": len(result["failed"]),
        }

    # ==================== 步骤 2：发薪方案创建 ====================

    def _step2_salary_scheme(self) -> Dict:
        """创建发薪方案

        HAR 确认的关键参数：
        - serviceCode: HRXZHS_MDD_030010
        - billnum: waschemelist / wascheme_addcard
        - 创建成功后系统自动生成45个默认薪资项目
        """
        api = self._init_api(SalarySchemeApi)
        scheme_name = self.config.get("scheme_name", "自动化测试方案")

        # 幂等检查
        existing = api.scheme_exists(scheme_name)
        if existing:
            scheme_id = existing.get("schemeId") or existing.get("id")
            self.context["scheme_id"] = scheme_id
            self.context["scheme_name"] = scheme_name
            self.context["scheme_version_id"] = existing.get("versionId", "")
            logger.info(f"  方案已存在: {scheme_name}, id={scheme_id}")
            return {"action": "skipped", "scheme_id": scheme_id}

        # 获取模板
        api.get_add_template()

        # 构造方案数据（基于 HAR 确认的完整结构）
        scheme_config = self.config.get("scheme", {})
        org_name = scheme_config.get("org_name", "企业账号级")
        scheme_code = scheme_config.get("code", "auto_test_scheme_001")

        scheme_data = {
            "busiOrg": self.org_id,
            "busiOrgName": org_name,
            "code": scheme_code,
            "editType": "add",
            "name": {
                "zh_CN": scheme_name,
                "id_ID": None,
                "es_ES": None,
                "pt_PT": None,
            },
            # 计薪周期
            "periodRuleId": scheme_config.get("periodRuleId", "2517185689663569924"),
            "periodRuleName": scheme_config.get("periodRuleName", "月"),
            # 起始/生效期间
            "startPeriod": scheme_config.get("startPeriod", "2517185715448578056"),
            "startPeriodName": scheme_config.get("startPeriodName", "2025-01"),
            "effectPeriod": scheme_config.get("effectPeriod", "2517185715448578056"),
            "effectPeriodName": scheme_config.get("effectPeriodName", "2025-01"),
            # 税务
            "tenant": "ppycw2h8",
            "deductionWay": scheme_config.get("deductionWay", "1"),
            "multiProjectIn": scheme_config.get("multiProjectIn", "0"),
            "projectIn": scheme_config.get("projectIn", "0"),
            "taxTable": scheme_config.get("taxTable", "cb17d85ee4d04f138745eca9f067f0d3"),
            "taxTableStr": scheme_config.get("taxTableStr", "居民税率表"),
            "taxCurrId": scheme_config.get("taxCurrId", "2517031809601503293"),
            "taxCurrName": scheme_config.get("taxCurrName", "人民币"),
            # 其他
            "approveFlag": "0",
            "settlementFlag": "0",
            "automaticMatchingFlag": "0",
            "scopeType": "0",
            "waSchemeCharacteristics": {},
            "scopeListKV": [],
            "schemeAuths": [],
            "_status": "Insert",
            # 适用范围
            "scopeStr": [
                {
                    "type": "org",
                    "scopes": [{"id": self.org_id, "name": org_name}]
                },
                {"type": "pcategory", "scopes": []},
                {"type": "jobrank", "scopes": []},
                {"type": "jobgrade", "scopes": []},
                {"type": "staffStatus", "scopes": []},
                {"type": "wagegroup", "scopes": []},
                {"type": "newpostid", "scopes": []},
                {"type": "parttype", "scopes": []},
            ]
        }

        result = api.save_scheme(scheme_data)
        scheme_id = result.get("schemeId") or result.get("id")
        self.context["scheme_id"] = scheme_id
        self.context["scheme_name"] = scheme_name
        self.context["scheme_version_id"] = result.get("versionId", "")

        return {
            "action": "created",
            "scheme_id": scheme_id,
            "version_id": result.get("versionId", ""),
        }

    # ==================== 步骤 3：发薪人员匹配 ====================

    def _step3_match_staff(self) -> Dict:
        """将HR系统员工匹配到发薪方案

        HAR 确认的流程：
        1. get_scheme_ref → 获取 schemeAuthId
        2. list_staff → 幂等检查
        3. get_available_staff → 获取可用员工
        4. get_tax_org → 获取扣缴义务人
        5. init_add → 初始化
        6. check → checkInsure → batchSave 三步保存
        """
        api = self._init_api(SalaryStaffApi)

        # 获取方案参照，找到目标方案的 schemeAuthId
        scheme_name = self.context.get("scheme_name", self.config.get("scheme_name"))
        scheme_refs = api.get_scheme_ref()

        scheme_ref = None
        for ref in scheme_refs:
            if ref.get("schemeName") == scheme_name:
                scheme_ref = ref
                break

        if not scheme_ref:
            raise RuntimeError(f"未在方案参照中找到: {scheme_name}")

        scheme_auth_id = scheme_ref["id"]
        tax_table_id = scheme_ref.get("taxTable", "")
        tax_table_name = scheme_ref.get("taxTableName", "")
        self.context["scheme_auth_id"] = scheme_auth_id

        logger.info(f"  方案参照: schemeAuthId={scheme_auth_id}, taxTable={tax_table_name}")

        # 幂等检查
        if api.has_staff(scheme_auth_id):
            data = api.list_staff(scheme_auth_id)
            records = data.get("recordList", [])
            self.context["staff_count"] = len(records)
            logger.info(f"  方案下已有 {len(records)} 名人员，跳过")
            return {"action": "skipped", "staff_count": len(records)}

        # 执行完整匹配流程
        begin_date = self.config.get("scheme", {}).get("startPeriodName", "2025-01") + "-01"
        result = api.match_staff_to_scheme(
            scheme_auth_id=scheme_auth_id,
            scheme_name=scheme_name,
            tax_table_id=tax_table_id,
            tax_table_name=tax_table_name,
            begin_date=begin_date,
        )

        staff_count = result.get("number", 0)
        self.context["staff_count"] = staff_count

        return {"action": "matched", "staff_count": staff_count}

    # ==================== 步骤 4：纳税人员同步 ====================

    def _step4_tax_person(self) -> Dict:
        """同步纳税人员

        HAR 确认的流程：
        - syncReportPerson 是一个 GET 请求，同步操作
        - orgId 参数使用 taxOrgId（税务组织ID），不是业务组织ID
        - 同步后通过 bill/list 验证结果
        """
        api = self._init_api(TaxPersonApi)

        # 使用完整流程封装（含幂等检查）
        result = api.sync_persons()

        self.context["tax_org_id"] = result.get("tax_org_id", "")
        self.context["tax_person_count"] = result.get("person_count", 0)

        return result

    # ==================== 步骤 5：专项附加扣除下载 ====================

    def _step5_special_deduction(self) -> Dict:
        """下载专项附加扣除数据

        HAR 确认的流程：
        - serviceCode: HRXZHS_MDD_040025
        - 两步机制: download（同步触发）→ query（异步，返回asyncKey）→ poll
        - orgId 使用 taxOrgId
        - taxMonth 格式: "2025-01-01"（月份第一天）
        """
        api = self._init_api(SpecialDeductionApi)
        tax_month = self.config.get("tax_month")  # 如 "2025-01"

        # 如果没配置 tax_month，从 scheme 的 startPeriodName 推导
        if not tax_month:
            tax_month = self.config.get("scheme", {}).get("startPeriodName", "2025-01")

        # 优先使用步骤4已获取的 tax_org_id
        tax_org_id = self.context.get("tax_org_id")

        # 使用完整流程封装（含幂等检查）
        result = api.download_deductions(tax_org_id=tax_org_id, tax_month=tax_month)

        self.context["deduction_tax_org_id"] = result.get("tax_org_id", "")
        self.context["deduction_count"] = result.get("person_count", 0)

        return result

    # ==================== 步骤 6：新建发放单并计算 ====================

    def _step6_pay_doc(self) -> Dict:
        """新建发放单并计算"""
        api = self._init_api(PayDocApi)
        doc_name = self.config.get("pay_doc_name", "自动化测试发放单")

        # 幂等检查
        existing = api.pay_doc_exists(doc_name)
        if existing:
            pay_file_id = existing["id"]
            self.context["pay_file_id"] = pay_file_id
            logger.info(f"  发放单已存在: {doc_name}, id={pay_file_id}")
            return {"action": "skipped", "pay_file_id": pay_file_id}

        # 创建发放单
        scheme_id = self.context.get("scheme_id")
        doc_data = {
            "name": {"zh_CN": doc_name},
            "busiOrg": self.org_id,
            "busiOrgVid": self.org_id,
            "busiOrgName": "企业账号级",
            "schemeId": scheme_id,
            "_status": "Insert",
            # 以下字段待 HAR 分析后补充
        }

        result = api.create_pay_doc(doc_data)
        pay_file_id = result.get("id")
        self.context["pay_file_id"] = pay_file_id

        # 验证计算条件
        api.verify_calculate(pay_file_id)

        # 执行计算
        query_id_str = f"{int(time.time() * 1000)}{pay_file_id}"
        self.context["query_id_str"] = query_id_str
        api.calculate(pay_file_id, query_id_str)

        # 等待计算完成
        success = api.wait_calculate_complete(pay_file_id, timeout=120)
        if not success:
            raise RuntimeError("发放单计算超时")

        return {
            "action": "created_and_calculated",
            "pay_file_id": pay_file_id,
            "query_id_str": query_id_str
        }

    # ==================== 辅助方法 ====================

    def _save_results(self):
        """保存执行结果"""
        output_path = Path(__file__).parent / "data" / "preset_run_result.yaml"
        os.makedirs(output_path.parent, exist_ok=True)

        output = {
            "run_info": {
                "start_time": self.results["start_time"],
                "end_time": self.results["end_time"],
                "base_url": self.base_url,
                "org_id": self.org_id,
            },
            "context": self.context,
            "steps": self.results["steps"]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info(f"\n执行结果已保存至: {output_path}")

    def _print_summary(self):
        """打印执行摘要"""
        logger.info(f"\n{'='*60}")
        logger.info("  预置执行摘要")
        logger.info(f"{'='*60}")

        for step_num, step_data in sorted(self.results["steps"].items()):
            status_icon = "✓" if step_data["status"] == "success" else "✗"
            logger.info(f"  {status_icon} 步骤{step_num} [{step_data['name']}]: {step_data['status']}")

        logger.info(f"\n  关键数据:")
        logger.info(f"    方案ID: {self.context.get('scheme_id', '未生成')}")
        logger.info(f"    发放单ID: {self.context.get('pay_file_id', '未生成')}")
        logger.info(f"    人员数: {self.context.get('staff_count', 0)}")
        logger.info(f"{'='*60}")


if __name__ == "__main__":
    runner = PresetRunner()
    runner.run()
