"""路径工具：统一管理项目根目录，避免路径硬编码"""
import os
import sys

# 项目根目录（当前文件向上找，有 run.py 或 app.py 的目录）
_PROJECT_ROOT = None


def _find_project_root():
    """从当前文件往上找，找到项目根（包含 run.py 的目录）"""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # 最多往上 5 层
        if os.path.exists(os.path.join(current, "run.py")) or \
           os.path.exists(os.path.join(current, "app.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.dirname(os.path.abspath(__file__))


def get_project_root() -> str:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = _find_project_root()
    return _PROJECT_ROOT


def get_abs_path(*segments: str) -> str:
    """拼接到项目根目录下的绝对路径"""
    return os.path.join(get_project_root(), *segments)
