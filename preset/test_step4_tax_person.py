"""步骤4 测试脚本：纳税人员同步

验证 TaxPersonApi 的完整流程：
1. get_tax_org → 查询税务组织
2. list_persons → 检查已有纳税人员
3. sync_report_person → 执行同步（如需要）
4. 验证同步结果

使用方式：
    export YONYOU_COOKIE="..."
    export YONYOU_XSRF_TOKEN="..."
    cd LuminaPayroll
    python3 preset/test_step4_tax_person.py
"""

import os
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from preset.preset_utils import create_authenticated_session
from pages.api.tax_person_api import TaxPersonApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    base_url = os.getenv("LUMINA_BASE_URL", "https://c4.yonyoucloud.com")
    org_id = "2517046541330939914"  # 壹贰叁
    xsrf_token = os.getenv("YONYOU_XSRF_TOKEN", "")

    session = create_authenticated_session()
    api = TaxPersonApi(base_url=base_url, session=session, org_id=org_id)
    if xsrf_token:
        api.set_xsrf_token(xsrf_token)

    print("\n" + "=" * 60)
    print("  步骤4 测试：纳税人员同步")
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

    # 2. 查询已有纳税人员
    print("\n--- 2) 查询已有纳税人员 ---")
    data = api.list_persons(tax_org_id)
    record_count = data.get("recordCount", 0)
    records = data.get("recordList", [])
    print(f"  总记录数: {record_count}")
    if records:
        print(f"  前几条记录:")
        for r in records[:5]:
            name = r.get("staffName", r.get("name", "未知"))
            print(f"    - {name}")

    # 3. 执行完整 sync_persons 流程
    print("\n--- 3) 执行 sync_persons 完整流程 ---")
    result = api.sync_persons(tax_org_id=tax_org_id)
    print(f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 4. 再次查询验证
    print("\n--- 4) 验证同步后的人员列表 ---")
    data = api.list_persons(tax_org_id)
    record_count = data.get("recordCount", 0)
    records = data.get("recordList", [])
    print(f"  同步后总记录数: {record_count}")
    if records:
        print(f"  人员列表:")
        for r in records[:10]:
            name = r.get("staffName", r.get("name", "未知"))
            print(f"    - {name}")

    print("\n" + "=" * 60)
    print(f"  步骤4 测试完成！action={result['action']}, 人员数={result['person_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
