"""在目标环境中批量预置公共薪资项目

使用说明：
    1. 先运行 export_salary_items.py 从标准环境导出模板
    2. 设置目标环境的 YONYOU_COOKIE 和 YONYOU_XSRF_TOKEN
    3. 运行：python preset/preset_salary_items.py
    4. 脚本会逐个检查 → 创建，已存在的自动跳过

预置流程（每个项目）：
    1. bill/list 查询项目是否已存在（按名称）
    2. 已存在 → 跳过，记录已有 ID
    3. 不存在 → bill/add 获取模板 → bill/save 创建项目
    4. 记录创建结果（ID, code）

幂等性保证：
    - 按项目名称做存在性判断，重复执行不会重复创建
    - 每次执行结果写入 preset_result.yaml 供后续步骤使用
"""

import os
import sys
import json
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pages.api.salary_item_api import SalaryItemApi
from preset.preset_utils import create_authenticated_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class SalaryItemPreset:
    """公共薪资项目预置执行器"""

    def __init__(self, base_url: str = None, org_id: str = "666666"):
        self.base_url = base_url or os.getenv("LUMINA_BASE_URL", "https://c4.yonyoucloud.com")
        self.org_id = org_id

        # 创建认证 Session
        session = create_authenticated_session()
        self.api = SalaryItemApi(
            base_url=self.base_url, session=session, org_id=self.org_id
        )
        xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")
        if xsrf_token:
            self.api.set_xsrf_token(xsrf_token)

        # 预置结果记录
        self.results = {
            "created": [],    # 本次新建的
            "skipped": [],    # 已存在跳过的
            "failed": [],     # 创建失败的
        }

        # 缓存：分类树和模板
        self._category_tree = None
        self._add_template = None

    def run(self, template_path: str = None, delay: float = 0.5) -> Dict:
        """执行批量预置

        Args:
            template_path: 模板文件路径
            delay: 每次创建间隔（秒），避免请求过快

        Returns:
            预置结果统计
        """
        template_path = template_path or str(
            Path(__file__).parent / "data" / "salary_items_template.yaml"
        )

        # 加载模板
        logger.info(f"加载模板: {template_path}")
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

        items = template_data.get("items", [])
        total = len(items)
        logger.info(f"共需预置 {total} 个薪资项目")

        # 预加载分类树和空白模板
        self._prepare()

        # 逐个预置
        for idx, item in enumerate(items, 1):
            name = item.get("name", "")
            logger.info(f"[{idx}/{total}] 处理: {name}")

            try:
                result = self._preset_one_item(item)
                if result["action"] == "created":
                    self.results["created"].append(result)
                    logger.info(f"  ✓ 创建成功: id={result['id']}, code={result['code']}")
                else:
                    self.results["skipped"].append(result)
                    logger.info(f"  → 已存在，跳过: id={result['id']}")
            except Exception as e:
                self.results["failed"].append({
                    "name": name,
                    "error": str(e)
                })
                logger.error(f"  ✗ 创建失败: {e}")

            # 间隔控制
            if delay > 0:
                time.sleep(delay)

        # 保存结果
        self._save_results()

        # 输出统计
        logger.info(f"\n{'='*50}")
        logger.info(f"预置完成:")
        logger.info(f"  新建: {len(self.results['created'])} 个")
        logger.info(f"  跳过: {len(self.results['skipped'])} 个")
        logger.info(f"  失败: {len(self.results['failed'])} 个")
        logger.info(f"{'='*50}")

        return self.results

    def _prepare(self):
        """预加载分类树和空白模板"""
        logger.info("预加载分类树...")
        self._category_tree = self.api.get_category_tree()

        logger.info("获取新建模板...")
        self._add_template = self.api.get_add_template()

    def _preset_one_item(self, item_config: Dict) -> Dict:
        """预置单个薪资项目

        Args:
            item_config: 从模板读取的项目配置

        Returns:
            {"action": "created"|"skipped", "name": ..., "id": ..., "code": ...}
        """
        name = item_config["name"]

        # 1. 检查是否已存在
        existing = self.api.item_exists(name)
        if existing:
            return {
                "action": "skipped",
                "name": name,
                "id": existing.get("id", ""),
                "code": existing.get("code", ""),
            }

        # 2. 构造创建数据
        save_data = self._build_save_data(item_config)

        # 3. 调用 bill/save 创建
        result = self.api.save_item(save_data)

        return {
            "action": "created",
            "name": name,
            "id": result.get("id", ""),
            "code": result.get("code", ""),
        }

    def _build_save_data(self, item_config: Dict) -> Dict:
        """根据模板配置构造 bill/save 所需的完整数据

        将 6 个差异字段 + 通用默认值组装成保存请求体
        """
        name_zh = item_config["name"]
        category_id = item_config.get("categoryId", "")
        category_name = item_config.get("categoryName", "")

        # 构造 businessRule（公式）
        # 如果模板中有 formulastr，需要包装成 businessRule JSON 结构
        formula_str = item_config.get("formulastr", "0")
        business_rule = self._build_business_rule(name_zh, formula_str)

        save_data = {
            # 名称（多语言对象）
            "name": {
                "zh_CN": name_zh,
                "id_ID": None,
                "es_ES": None,
                "pt_PT": None,
            },
            # 组织
            "busiOrg": self.org_id,
            "busiOrgVid": self.org_id,
            "busiOrgName": "企业账号级",
            # 分类
            "categoryId": category_id,
            "categoryName": category_name,
            # 6 个差异字段中的 4 个
            "dataType": item_config.get("dataType", "1"),
            "property": item_config.get("property", "0"),
            "taxFlag": item_config.get("taxFlag", "0"),
            # 公式
            "businessRuleName": name_zh,
            "businessRule": business_rule,
            # 通用默认值
            "fldDecimal": str(item_config.get("fldDecimal", 2)),
            "roundType": item_config.get("roundType", "4"),
            "fromFlag": item_config.get("fromFlag", "9"),
            "salaryChg": "0",
            "staticItemFlg": "0",
            "segmentAccount": "0",
            "salaryRule": None,
            "docFlag": "0",
            "customDocFlag": "0",
            "clearFlag": "1",
            "isDisplay": "1",
            "allowModify": "1",
            "effectPeriodSegment": "1",
            "segmentedSummaryRowRule": 0,
            "approveFlag": "0",
            "payslipFlag": "0",
            "scopeType": "0",
            # code 传 "f"，服务端会自动分配完整编码
            "code": "f",
            # 国家
            "country": item_config.get("country", "0040be98-735b-44c0-afe5-54d11a96037b"),
            "countryName": item_config.get("countryName", "中国大陆"),
            # 适用范围
            "waItemScopes": [
                {
                    "scopeFlag": "1",
                    "hasDefaultInit": True,
                    "scopeOrgName": "企业账号级",
                    "scopeOrgId": [self.org_id],
                    "_status": "Insert"
                }
            ],
            "waItemDefineCharacter": {},
            # 状态标记
            "_status": "Insert",
            "categoryCode": "HR_WA_ITEM_CN",
        }

        return save_data

    def _build_business_rule(self, name: str, formula_str: str) -> str:
        """构造 businessRule 字段

        businessRule 是一个 JSON 字符串，包含公式定义。
        简单公式直接用 formulastr 包装，复杂公式（含函数调用）保持原样。

        Args:
            name: 项目名称（作为规则名）
            formula_str: 公式字符串，如 "0" 或 "busiFun('calendar_day_count',...)"

        Returns:
            JSON 字符串格式的 businessRule
        """
        # 如果公式为空或 "0"，返回最简结构
        if not formula_str or formula_str == "0":
            rule = {
                "name": name,
                "formulastr": "0",
                "ruleItems": []
            }
        else:
            rule = {
                "name": name,
                "formulastr": formula_str,
                "ruleItems": [
                    {
                        "formula": formula_str,
                        "condFormula": "",
                        "condFormulaDisplay": "",
                        "formulaDisplay": formula_str
                    }
                ]
            }

        return json.dumps(rule, ensure_ascii=False)

    def _save_results(self):
        """保存预置结果到文件"""
        result_path = Path(__file__).parent / "data" / "preset_result.yaml"
        os.makedirs(result_path.parent, exist_ok=True)

        output = {
            "summary": {
                "created_count": len(self.results["created"]),
                "skipped_count": len(self.results["skipped"]),
                "failed_count": len(self.results["failed"]),
            },
            "created": self.results["created"],
            "skipped": self.results["skipped"],
            "failed": self.results["failed"],
        }

        with open(result_path, "w", encoding="utf-8") as f:
            yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info(f"预置结果已保存至: {result_path}")


if __name__ == "__main__":
    preset = SalaryItemPreset()
    preset.run()
