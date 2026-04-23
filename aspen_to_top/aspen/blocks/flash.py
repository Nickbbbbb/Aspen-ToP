from typing import Dict, Any, List
from .base import BaseBlockExtractor


class FlashExtractor(BaseBlockExtractor):
    """Flash2 闪蒸器提取器。

    只负责把 Aspen 的 Input 路径读成标准化 params，不关心 ToP 模板字段。
    ToP 字段怎么填由 converter/property_fillers.py 决定。
    """

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            # SPEC_OPT 控制闪蒸规格，例如 TP、PV。后续会映射到 Thermal_specification。
            "SPEC_OPT": FlashExtractor.get_prop(tree, fr"{base}\SPEC_OPT"),
            "system_pressure": FlashExtractor.get_prop(tree, fr"{base}\PRES"),
            "comp_nums": comp_count,
            "system_temperature": FlashExtractor.get_prop(tree, fr"{base}\TEMP"),
            "system_vapor_molar_fraction": FlashExtractor.get_prop(tree, fr"{base}\VFRAC"),
            "system_heat_duty": FlashExtractor.get_prop(tree, fr"{base}\DUTY"),
        }
