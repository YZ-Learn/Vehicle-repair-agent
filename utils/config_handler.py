"""YAML 配置加载器"""
import yaml
from typing import Any
from utils.path_tool import get_abs_path


def load_config(filename: str) -> dict[str, Any]:
    """从 config/ 目录加载 YAML 配置文件"""
    path = get_abs_path("config", filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
