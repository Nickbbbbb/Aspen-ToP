"""运行时路径工具。

本项目既支持源码方式运行，也支持 PyInstaller 打包后的 exe 运行。
两种模式下，模板目录、外部加密工具目录和输出目录的基准位置并不完全相同：

- 源码运行：资源和输出都默认以项目根目录为基准。
- exe 运行：打包进去的资源位于临时解包目录 `_MEIPASS`，输出更适合放在 exe 所在目录。

这里统一封装这些路径，避免每个模块都自己判断 `sys.frozen`。
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen_app() -> bool:
    """判断当前是否运行在 PyInstaller 打包后的 exe 中。"""
    return bool(getattr(sys, "frozen", False))


def get_resource_root() -> Path:
    """返回运行时资源根目录。

    - 源码运行时，返回项目根目录。
    - exe 运行时，返回 PyInstaller 解包后的临时目录。
    """
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_workspace_root() -> Path:
    """返回工作目录根路径。

    这个路径用于放输出文件，而不是读取模板资源：

    - 源码运行时，输出仍放在项目根目录。
    - exe 运行时，输出放在 exe 所在目录，方便命令行用户直接查看结果。
    """
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return get_resource_root()


RESOURCE_ROOT = get_resource_root()
WORKSPACE_ROOT = get_workspace_root()
TEMPLATE_DIR = RESOURCE_ROOT / "Template"
EXPORT_TOOL_DIR = RESOURCE_ROOT / "export-test"
DEFAULT_OUTPUT_DIR = WORKSPACE_ROOT / "output"
