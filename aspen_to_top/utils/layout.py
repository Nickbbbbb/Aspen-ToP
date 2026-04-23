import json
import re


def extract_coords_from_bkp(file_path: str, target_id: str):
    """从 .bkp 文件中提取指定对象的 flowsheet 坐标。

    Aspen COM Tree 对流程连接更友好，但坐标信息在当前代码中通过读取
    BKP 原始文本片段获得。target_id 可以是设备名，也可以是流股名：
    - 设备节点读取 Block 名，例如 FENLV、HOT。
    - Source/Sink 读取流股名，例如 S1、S2、S7。

    找不到坐标时返回 0,0，避免坐标缺失导致转换失败。
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read().decode('latin-1', errors='ignore')

        # BKP 中坐标通常出现在 "ID: xxx ... At x y" 附近。
        pattern = rf"ID:\s+{re.escape(target_id)}\b(?:(?!BLOCK).)*?At\s+([\d\.-]+)\s+([\d\.-]+)"
        match = re.search(pattern, raw_data, re.DOTALL)

        if match:
            x, y = match.groups()
            return {"id": target_id, "x": float(x), "y": float(y)}
        return {"id": target_id, "x": 0, "y": 0}
    except Exception:
        return {"id": target_id, "x": 0, "y": 0}


class LayoutFixer:
    """流程图布局修复工具。

    主转换链路已经在 graph_builder 中写入坐标；这个类主要保留给调试或
    后处理场景，例如拿一个已有 ToP JSON 重新按 BKP 坐标修复布局。
    """

    @staticmethod
    def fix_layout(data: dict, bkp_path: str = None) -> dict:
        """按 BKP 中的坐标重写 processNodes 的 x/y。"""
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
        """兜底网格布局。

        当 BKP 坐标不可用但仍希望 ToP 中节点不要重叠时，可以使用该方法。
        """
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
