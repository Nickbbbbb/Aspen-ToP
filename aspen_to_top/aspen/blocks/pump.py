from typing import Dict, Any, List
from .base import BaseBlockExtractor


class PumpExtractor(BaseBlockExtractor):
    """Pump 泵提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "OPT_SPEC": PumpExtractor.get_prop(tree, fr"{base}\OPT_SPEC"),
            "outlet_stream_pressure": PumpExtractor.get_prop(tree, fr"{base}\PRES"),
            "pressure_increase": PumpExtractor.get_prop(tree, fr"{base}\DELP"),
            "pressure_ratio": PumpExtractor.get_prop(tree, fr"{base}\PRATIO"),
            "total_power": PumpExtractor.get_prop(tree, fr"{base}\POWER"),
            "comp_nums": comp_count,
            "pumping_efficiency": PumpExtractor.get_prop(tree, fr"{base}\EFF"),
        }
