"""从标准环境导出所有公共薪资项目数据

使用说明：
    1. 设置环境变量 YONYOU_COOKIE（从标准环境浏览器复制）
    2. 可选设置 YONYOU_XSRF_TOKEN
    3. 运行脚本：python preset/export_salary_items.py
    4. 导出结果保存到 preset/data/salary_items_template.yaml

导出内容包含创建项目所需的 6 个差异字段：
    - name: 项目名称
    - categoryId/categoryName: 分类
    - businessRule: 公式
    - dataType: 数据类型
    - property: 增减属性
    - taxFlag: 个税申报属性
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pages.api.salary_item_api import SalaryItemApi
from preset.preset_utils import create_authenticated_session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def export_salary_items(base_url: str = None, org_id: str = "666666",
                        output_path: str = None) -> str:
    """从标准环境导出所有薪资项目

    Args:
        base_url: 标准环境 URL
        org_id: 组织 ID
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    base_url = base_url or os.getenv("LUMINA_BASE_URL", "https://c4.yonyoucloud.com")
    output_path = output_path or str(
        Path(__file__).parent / "data" / "salary_items_template.yaml"
    )

    # 创建认证 Session
    session = create_authenticated_session()

    # 初始化 API
    api = SalaryItemApi(base_url=base_url, session=session, org_id=org_id)
    xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")
    if xsrf_token:
        api.set_xsrf_token(xsrf_token)

    # 1. 获取分类树（导出分类名称映射）
    logger.info("正在获取分类树...")
    category_tree = api.get_category_tree()
    category_map = _flatten_category_tree(category_tree)
    logger.info(f"共获取 {len(category_map)} 个分类")

    # 2. 分页导出所有项目
    logger.info("正在导出所有薪资项目...")
    all_items = api.list_all_items(page_size=50)
    logger.info(f"共导出 {len(all_items)} 个薪资项目")

    # 3. 提取创建所需字段，构造模板
    template_items = []
    for item in all_items:
        template_item = _extract_item_fields(item, category_map)
        template_items.append(template_item)

    # 4. 构造输出结构
    output_data = {
        "meta": {
            "source_env": base_url,
            "org_id": org_id,
            "total_count": len(template_items),
            "export_note": "从标准环境导出，用于目标环境预置"
        },
        "categories": [
            {"id": k, "name": v} for k, v in category_map.items()
        ],
        "items": template_items
    }

    # 5. 保存到文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    logger.info(f"导出完成，保存至: {output_path}")
    return output_path


def _flatten_category_tree(tree_data: list) -> Dict[str, str]:
    """展平分类树为 {categoryId: categoryName} 映射"""
    result = {}

    def _walk(nodes):
        for node in nodes:
            key = node.get("key", "")
            title = node.get("title", "")
            if key and key != "x":  # 跳过根节点
                result[key] = title
            children = node.get("children", [])
            if children:
                _walk(children)

    _walk(tree_data)
    return result


def _extract_item_fields(item: dict, category_map: dict) -> dict:
    """从查询结果中提取创建所需的关键字段

    6 个差异字段 + 辅助字段
    """
    name_value = item.get("name", "")
    # name 可能是多语言对象或字符串
    if isinstance(name_value, dict):
        name_zh = name_value.get("zh_CN", "")
    else:
        name_zh = str(name_value)

    category_id = item.get("categoryId", "")
    category_name = item.get("categoryName", "") or category_map.get(category_id, "")

    return {
        # === 6 个差异字段 ===
        "name": name_zh,
        "categoryId": category_id,
        "categoryName": category_name,
        "dataType": str(item.get("dataType", "1")),
        "property": str(item.get("property", "0")),
        "taxFlag": str(item.get("taxFlag", "0")),
        # === 公式相关 ===
        "businessRuleId": item.get("businessRuleId", ""),
        "businessRuleName": item.get("businessRuleName", ""),
        "formulastr": item.get("formulastr", ""),
        # === 辅助字段（创建时可能需要） ===
        "fldDecimal": item.get("fldDecimal", 2),
        "roundType": str(item.get("roundType", "4")),
        "fromFlag": str(item.get("fromFlag", "9")),
        "country": item.get("country", ""),
        "countryName": item.get("countryName", ""),
        # === 标识（仅记录，创建时由系统生成） ===
        "original_id": item.get("id", ""),
        "original_code": item.get("code", ""),
    }


if __name__ == "__main__":
    export_salary_items()
