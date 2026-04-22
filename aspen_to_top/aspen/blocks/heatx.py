from typing import Dict, Any, List
from .base import BaseBlockExtractor


class HeatXExtractor(BaseBlockExtractor):
    """HeatX 换热器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "hot_outlet_pressure": HeatXExtractor.get_prop(tree, fr"{base}\PRES_HOT"),
            "cold_outlet_pressure": HeatXExtractor.get_prop(tree, fr"{base}\PRES_COLD"),
            "comp_nums": comp_count,
            "area": HeatXExtractor.get_prop(tree, fr"{base}\AREA"),
            "u_overall": HeatXExtractor.get_prop(tree, fr"{base}\U"),
        }
