import json
import re


def extract_coords_from_bkp(file_path: str, target_id: str):
    """从 .bkp 二进制文件中提取指定 Block 的坐标"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read().decode('latin-1', errors='ignore')

        pattern = rf"ID:\s+{re.escape(target_id)}\b(?:(?!BLOCK).)*?At\s+([\d\.-]+)\s+([\d\.-]+)"
        match = re.search(pattern, raw_data, re.DOTALL)

        if match:
            x, y = match.groups()
            return {"id": target_id, "x": float(x), "y": float(y)}
        return {"id": target_id, "x": 0, "y": 0}
    except Exception:
        return {"id": target_id, "x": 0, "y": 0}


class LayoutFixer:
    """流程图布局修复工具"""

    @staticmethod
    def fix_layout(data: dict, bkp_path: str = None) -> dict:
        graph = data.get('omProcessGraph', {})
        nodes_str = graph.get('processNodes', '[]')
        nodes = json.loads(nodes_str) if isinstance(nodes_str, str) else nodes_str

        for node in nodes:
            if bkp_path and 'label' in node.get('data', {}):
                label = node['data']['label']
                coords = extract_coords_from_bkp(bkp_path, label)
                node['x'] = coords["x"] * 100
                node['y'] = coords["y"] * -100

        graph['processNodes'] = json.dumps(nodes) if isinstance(nodes_str, str) else nodes
        return data

    @staticmethod
    def grid_layout(data: dict, grid_cols: int = 5, x_spacing: int = 300, y_spacing: int = 200) -> dict:
        graph = data.get('omProcessGraph', {})
        nodes_str = graph.get('processNodes', '[]')
        nodes = json.loads(nodes_str) if isinstance(nodes_str, str) else nodes_str

        for i, node in enumerate(nodes):
            row = i // grid_cols
            col = i % grid_cols
            node['x'] = 100 + (col * x_spacing)
            node['y'] = 100 + (row * y_spacing)
            if 'data' in node:
                node['data']['status'] = ""

        graph['processNodes'] = json.dumps(nodes) if isinstance(nodes_str, str) else nodes
        return data
