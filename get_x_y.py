import re


def extract_coords_from_bkp(file_path, target_id):
    """
    直接从 .bkp 二进制文件中提取指定 Block 的坐标
    """
    try:
        # 使用 'rb' 读取，然后忽略错误解码为 latin-1，
        # 因为 bkp 含有大量非文本二进制字符，utf-8 会报错
        with open(file_path, 'rb') as f:
            raw_data = f.read().decode('latin-1', errors='ignore')

        # 正则表达式说明：
        # ID:\s+{target_id}  匹配目标 ID
        # (?:(?!BLOCK).)*?   非贪婪匹配，直到遇到下一个 BLOCK 标识（确保在同一个块内）
        # At\s+([\d\.-]+)\s+([\d\.-]+) 抓取 X 和 Y 坐标
        pattern = rf"ID:\s+{re.escape(target_id)}\b(?:(?!BLOCK).)*?At\s+([\d\.-]+)\s+([\d\.-]+)"

        match = re.search(pattern, raw_data, re.DOTALL)

        if match:
            x, y = match.groups()
            return {"id": target_id, "x": float(x), "y": float(y)}
        else:
            return {"id": target_id, "x": 0, "y": 0}

    except Exception as e:
        return f"处理文件时出错: {str(e)}"


# 使用示例
file_path = r"C:\Users\Administrator\Downloads\export-test\aspen_result\all_process\all_process.bkp"
target = "E-313X"
result = extract_coords_from_bkp(file_path, target)
print(result)