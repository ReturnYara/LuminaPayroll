import json
import yaml
from pathlib import Path
from typing import Dict, Any


def read_test_data(file_path: str) -> Dict[str, Any]:
    """读取测试数据"""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix == ".json":
            return json.load(f)
        elif path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")


def save_test_data(data: Dict[str, Any], file_path: str):
    """保存测试数据"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix == ".json":
            json.dump(data, f, ensure_ascii=False, indent=2)
        elif path.suffix in (".yaml", ".yml"):
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def generate_timestamp() -> str:
    """生成时间戳"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
