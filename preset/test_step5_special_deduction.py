"""步骤5 测试脚本：专项附加扣除下载

验证 SpecialDeductionApi 的完整流程：
1. get_tax_org → 查询税务组织
2. is_downloaded → 检查是否已下载过
3. download → 同步触发下载
4. query + poll → 异步查询并等待
5. list_deductions → 验证结果

使用方式：
    export YONYOU_COOKIE="..."
    export YONYOU_XSRF_TOKEN="..."
    cd LuminaPayroll
    python3 preset/test_step5_special_deduction.py
"""

import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from preset.preset_utils import create_authenticated_session
from pages.api.special_deduction_api import SpecialDeductionApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 配置
TAX_MONTH = "2025-01"  # 与方案起始期间一致


def main():
    base_url = os.getenv("LUMINA_BASE_URL", "https://c4.yonyoucloud.com")
    org_id = "2517046541330939914"  # 壹贰叁
    xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")

    session = create_authenticated_session()
    api = SpecialDeductionApi(base_url=base_url, session=session, org_id=org_id)
    if xsrf_token:
        api.set_xsrf_token(xsrf_token)

    print("\n" + "=" * 60)
    print("  步骤5 测试：专项附加扣除下载")
    print("=" * 60)

    # 1. 查询税务组织
    print("\n--- 1) 查询税务组织 ---")
    tax_orgs = api.get_tax_org()
    print(f"  找到 {len(tax_orgs)} 个税务组织:")
    for org in tax_orgs:
        print(f"    - id={org.get('id')}, name={org.get('taxName')}, "
              f"taxNo={org.get('taxMemberNumber', 'N/A')}")

    if not tax_orgs:
        print("  [ERROR] 未找到税务组织，无法继续")
        return

    tax_org_id = tax_orgs[0]["id"]
    print(f"  使用第一个税务组织: id={tax_org_id}")

    # 2. 检查是否已下载
    print(f"\n--- 2) 检查 {TAX_MONTH} 是否已下载 ---")
    downloaded = api.is_downloaded(tax_org_id, TAX_MONTH)
    print(f"  已下载: {downloaded}")

    # 3. 查询已有数据
    month_first = f"{TAX_MONTH}-01"
    import calendar
    y, m = int(TAX_MONTH.split("-")[0]), int(TAX_MONTH.split("-")[1])
    month_last = f"{TAX_MONTH}-{calendar.monthrange(y, m)[1]:02d}"

    print(f"\n--- 3) 查询已有扣除数据 ({month_first} ~ {month_last}) ---")
    data = api.list_deductions(tax_org_id, month_first, month_last)
    records = data.get("recordList", [])
    print(f"  记录数: {len(records)}")
    if records:
        for r in records[:5]:
            name = r.get("staffName", "未知")
            total = r.get("accumDeductTotal", 0)
            print(f"    - {name}: 累计扣除={total}")

    # 4. 执行完整 download_deductions 流程
    print(f"\n--- 4) 执行完整下载流程 (tax_month={TAX_MONTH}) ---")
    result = api.download_deductions(tax_org_id=tax_org_id, tax_month=TAX_MONTH)
    print(f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 5. 再次查询验证
    print(f"\n--- 5) 验证下载后的数据 ---")
    data = api.list_deductions(tax_org_id, month_first, month_last)
    records = data.get("recordList", [])
    print(f"  最终记录数: {len(records)}")
    if records:
        for r in records[:10]:
            name = r.get("staffName", "未知")
            total = r.get("accumDeductTotal", 0)
            child = r.get("childEduExpense", 0)
            house = r.get("houseLoanInterest", 0)
            print(f"    - {name}: 累计={total}, 子女教育={child}, 房贷利息={house}")

    print("\n" + "=" * 60)
    print(f"  步骤5 测试完成！action={result['action']}, 人员数={result['person_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
