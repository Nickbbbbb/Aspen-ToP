#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HSS文件加解密工具

用法:
    解密: python hss_file_tool.py decrypt input.hss output.json
    加密: python hss_file_tool.py encrypt input.json output.hss

依赖安装:
    pip install pycryptodome
"""

import sys
import json
import base64
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    print("请先安装依赖: pip install pycryptodome")
    sys.exit(1)

# 加密配置 (与Java代码保持一致)
KEY = b"MDEyMzQ1Njc4OTAxMjM0NQ=="  # 24字节 -> AES-192
IV = b"1234567890123456"            # 16字节


def decrypt_hss(input_file: str, output_file: str):
    """解密 HSS 文件为 JSON"""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")

    print(f"正在解密: {input_path.absolute()}")

    # 读取加密内容
    encrypted_content = input_path.read_text(encoding='utf-8')

    # Base64解码
    encrypted_bytes = base64.b64decode(encrypted_content)

    # AES解密
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)
    json_content = decrypted_bytes.decode('utf-8')

    # 格式化JSON输出
    data = json.loads(json_content)
    formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
    output_path.write_text(formatted_json, encoding='utf-8')

    print(f"解密成功: {output_path.absolute()}")
    print(f"文件大小: {output_path.stat().st_size} bytes")

    # 打印基本信息
    if 'omProject' in data and data['omProject']:
        project = data['omProject']
        print(f"项目名称: {project.get('projectName', 'N/A')}")
        print(f"项目ID: {project.get('id', 'N/A')}")


def encrypt_json(input_file: str, output_file: str):
    """加密 JSON 文件为 HSS"""
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")

    print(f"正在加密: {input_path.absolute()}")

    # 读取JSON内容
    json_content = input_path.read_text(encoding='utf-8')

    # 验证JSON格式
    data = json.loads(json_content)

    # 重新序列化(去除格式化，减小体积)
    compact_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    # AES加密
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    padded_data = pad(compact_json.encode('utf-8'), AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_data)

    # Base64编码
    encrypted_content = base64.b64encode(encrypted_bytes).decode('utf-8')
    output_path.write_text(encrypted_content, encoding='utf-8')

    print(f"加密成功: {output_path.absolute()}")
    print(f"文件大小: {output_path.stat().st_size} bytes")

    # 打印基本信息
    if 'omProject' in data and data['omProject']:
        project = data['omProject']
        print(f"项目名称: {project.get('projectName', 'N/A')}")


def print_usage():
    print("HSS文件加解密工具")
    print()
    print("用法:")
    print("  解密HSS为JSON: python hss_file_tool.py decrypt <input.hss> <output.json>")
    print("  加密JSON为HSS: python hss_file_tool.py encrypt <input.json> <output.hss>")
    print()
    print("示例:")
    print("  python hss_file_tool.py decrypt project.hss project.json")
    print("  python hss_file_tool.py encrypt project.json project.hss")
    print()
    print("依赖安装:")
    print("  pip install pycryptodome")


def main():
    if len(sys.argv) < 4:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    input_file = sys.argv[2]
    output_file = sys.argv[3]

    try:
        if command == "decrypt":
            decrypt_hss(input_file, output_file)
        elif command == "encrypt":
            encrypt_json(input_file, output_file)
        else:
            print(f"未知命令: {command}")
            print_usage()
            sys.exit(1)
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
