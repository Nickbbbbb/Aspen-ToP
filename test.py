#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aspen-ToP 工具测试文件

该文件提供了多种测试方法，帮助用户检验 Aspen BKP 到 ToP HSS 的转换功能。

使用方法：
    python test.py api         # 测试 API 函数
    python test.py cli         # 测试命令行工具
    python test.py batch       # 测试批量转换
    python test.py help        # 显示帮助信息
"""

import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from aspen_to_top import (
    convert_bkp_to_hss,
    extract_bkp_data,
    build_top_json,
    encrypt_to_hss,
    decrypt_hss
)


def test_api():
    """测试 API 函数"""
    print("=" * 60)
    print("🧪 测试 API 函数")
    print("=" * 60)

    # 测试单个文件转换
    print("\n1. 测试单个文件转换")
    print("-" * 40)
    try:
        # 这里需要替换为实际的 BKP 文件路径
        bkp_file = "example.bkp"
        if Path(bkp_file).exists():
            result = convert_bkp_to_hss(bkp_file)
            print(f"✅ 单个文件转换成功: {result}")
        else:
            print(f"⚠️  测试文件不存在: {bkp_file}")
            print("   请将测试 BKP 文件重命名为 example.bkp 或修改测试代码中的路径")
    except Exception as e:
        print(f"❌ 单个文件转换失败: {e}")

    # 测试分步操作
    print("\n2. 测试分步操作")
    print("-" * 40)
    try:
        bkp_file = "example.bkp"
        if Path(bkp_file).exists():
            # Step 1: 提取数据
            json_file = extract_bkp_data(bkp_file, "test_extracted.json")
            print(f"✅ 数据提取成功: {json_file}")

            # Step 2: 构建 JSON
            top_json = build_top_json("test_extracted.json", "test_top.json")
            print(f"✅ JSON 构建成功: {top_json}")

            # Step 3: 加密为 HSS
            hss_file = encrypt_to_hss("test_top.json", "test_output.hss")
            print(f"✅ 加密成功: {hss_file}")

            # Step 4: 解密测试
            decrypted_json = decrypt_hss("test_output.hss", "test_decrypted.json")
            print(f"✅ 解密成功: {decrypted_json}")
        else:
            print(f"⚠️  测试文件不存在: {bkp_file}")
    except Exception as e:
        print(f"❌ 分步操作失败: {e}")

    # 测试批量转换
    print("\n3. 测试批量转换")
    print("-" * 40)
    try:
        # 查找当前目录下的所有 BKP 文件
        bkp_files = list(Path(".").glob("*.bkp"))
        if bkp_files:
            print(f"找到 {len(bkp_files)} 个 BKP 文件:")
            for f in bkp_files:
                print(f"  - {f.name}")
            
            results = convert_bkp_to_hss(bkp_files)
            print(f"\n✅ 批量转换成功: {len(results)} 个文件")
            for r in results:
                print(f"  - {r}")
        else:
            print("⚠️  当前目录没有找到 BKP 文件")
    except Exception as e:
        print(f"❌ 批量转换失败: {e}")


def test_cli():
    """测试命令行工具"""
    print("=" * 60)
    print("🧪 测试命令行工具")
    print("=" * 60)

    # 显示帮助信息
    print("\n1. 显示帮助信息")
    print("-" * 40)
    os.system("python aspen_to_top/main.py --help")

    # 测试单个文件转换
    print("\n2. 测试单个文件转换")
    print("-" * 40)
    bkp_file = "example.bkp"
    if Path(bkp_file).exists():
        cmd = f"python aspen_to_top/main.py {bkp_file}"
        print(f"执行命令: {cmd}")
        os.system(cmd)
    else:
        print(f"⚠️  测试文件不存在: {bkp_file}")

    # 测试指定输出
    print("\n3. 测试指定输出")
    print("-" * 40)
    if Path(bkp_file).exists():
        cmd = f"python aspen_to_top/main.py {bkp_file} -o test_cli.hss"
        print(f"执行命令: {cmd}")
        os.system(cmd)
    else:
        print(f"⚠️  测试文件不存在: {bkp_file}")

    # 测试保存中间文件
    print("\n4. 测试保存中间文件")
    print("-" * 40)
    if Path(bkp_file).exists():
        cmd = f"python aspen_to_top/main.py {bkp_file} -i"
        print(f"执行命令: {cmd}")
        os.system(cmd)
    else:
        print(f"⚠️  测试文件不存在: {bkp_file}")


def test_batch():
    """测试批量转换"""
    print("=" * 60)
    print("🧪 测试批量转换")
    print("=" * 60)

    # 查找当前目录下的所有 BKP 文件
    bkp_files = list(Path(".").glob("*.bkp"))
    if bkp_files:
        print(f"找到 {len(bkp_files)} 个 BKP 文件:")
        for f in bkp_files:
            print(f"  - {f.name}")
        
        # 使用 API 进行批量转换
        print("\n使用 API 批量转换:")
        results = convert_bkp_to_hss(bkp_files)
        print(f"✅ 批量转换完成: {len(results)} 个文件")
        for r in results:
            print(f"  - {r}")
    else:
        print("⚠️  当前目录没有找到 BKP 文件")
        print("请将测试 BKP 文件放在当前目录")


def show_help():
    """显示帮助信息"""
    print("=" * 60)
    print("📖 Aspen-ToP 测试工具")
    print("=" * 60)
    print("使用方法:")
    print("  python test.py api         # 测试 API 函数")
    print("  python test.py cli         # 测试命令行工具")
    print("  python test.py batch       # 测试批量转换")
    print("  python test.py help        # 显示帮助信息")
    print()
    print("测试前准备:")
    print("  1. 确保安装了依赖: pip install pywin32 pycryptodome")
    print("  2. 准备 Aspen BKP 测试文件")
    print("  3. 确保 Template 目录存在")
    print()
    print("示例 BKP 文件:")
    print("  - 将测试 BKP 文件命名为 example.bkp")
    print("  - 或修改测试代码中的文件路径")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Aspen-ToP 测试工具")
    parser.add_argument("mode", nargs="?", default="help", choices=["api", "cli", "batch", "help"],
                        help="测试模式")
    args = parser.parse_args()

    if args.mode == "api":
        test_api()
    elif args.mode == "cli":
        test_cli()
    elif args.mode == "batch":
        test_batch()
    else:
        show_help()


if __name__ == "__main__":
    main()
