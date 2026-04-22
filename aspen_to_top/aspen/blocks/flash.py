from typing import Dict, Any, List
from .base import BaseBlockExtractor


class FlashExtractor(BaseBlockExtractor):
    """Flash2 闪蒸器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "SPEC_OPT": FlashExtractor.get_prop(tree, fr"{base}\SPEC_OPT"),
            "system_pressure": FlashExtractor.get_prop(tree, fr"{base}\PRES"),
            "comp_nums": comp_count,
            "system_temperature": FlashExtractor.get_prop(tree, fr"{base}\TEMP"),
            "system_vapor_molar_fraction": FlashExtractor.get_prop(tree, fr"{base}\VFRAC"),
            "system_heat_duty": FlashExtractor.get_prop(tree, fr"{base}\DUTY"),
        }
