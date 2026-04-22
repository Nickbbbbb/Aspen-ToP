#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 aspen_result 文件夹中的 BKP 文件进行测试
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from aspen_to_top import convert_bkp_to_hss

def test_with_aspen_result_files():
    """使用 aspen_result 文件夹中的文件测试"""
    print("=" * 60)
    print("使用 aspen_result 文件夹中的文件测试")
    print("=" * 60)

    # 定义测试文件路径
    project_root = Path(__file__).parent
    aspen_result_dir = project_root / "aspen_result"

    # 测试文件列表
    test_files = [
        aspen_result_dir / "flash" / "flash.bkp",
        aspen_result_dir / "flash_test" / "flash_test.bkp",
        aspen_result_dir / "flash_single" / "flash_single.bkp",
        aspen_result_dir / "heater_test" / "heater_test.bkp",
        aspen_result_dir / "pump_test" / "pump_test.bkp",
    ]

    # 检查文件是否存在
    existing_files = []
    for file_path in test_files:
        if file_path.exists():
            existing_files.append(file_path)
            print(f"找到测试文件: {file_path.relative_to(project_root)}")
        else:
            print(f"文件不存在: {file_path.relative_to(project_root)}")

    if not existing_files:
        print("\n没有找到测试文件")
        return

    # 创建输出目录
    output_dir = project_root / "test_output"
    output_dir.mkdir(exist_ok=True)
    print(f"\n输出目录: {output_dir.relative_to(project_root)}")

    # 测试单个文件
    print("\n1. 测试单个文件转换")
    print("-" * 40)
    if existing_files:
        test_file = existing_files[0]
        print(f"测试文件: {test_file.relative_to(project_root)}")
        try:
            results = convert_bkp_to_hss(str(test_file), output_dir=str(output_dir))
            print(f"转换成功: {results}")
        except Exception as e:
            print(f"转换失败: {e}")

    # 测试批量转换
    print("\n2. 测试批量转换")
    print("-" * 40)
    if len(existing_files) >= 2:
        print(f"批量测试 {len(existing_files)} 个文件")
        try:
            results = convert_bkp_to_hss([str(f) for f in existing_files], output_dir=str(output_dir))
            print(f"批量转换成功: {len(results)} 个文件")
            for r in results:
                print(f"  - {Path(r).relative_to(project_root)}")
        except Exception as e:
            print(f"批量转换失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_with_aspen_result_files()
