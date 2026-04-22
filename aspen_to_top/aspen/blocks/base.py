from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseBlockExtractor(ABC):
    """设备参数提取器基类"""

    @staticmethod
    @abstractmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        pass

    @staticmethod
    def get_prop(tree, path: str, default_unit: str = "") -> Dict[str, Any]:
        try:
            node = tree.FindNode(path)
            if node:
                unit = getattr(node, "UnitString", default_unit)
                val = node.Value
                if val is None:
                    val = 0.0
                return {"value": val, "unit": unit}
            return {"value": None, "unit": default_unit}
        except Exception:
            return {"value": None, "unit": default_unit}
