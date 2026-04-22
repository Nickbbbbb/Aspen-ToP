from typing import Dict, Any, List
from .base import BaseBlockExtractor


class HeaterExtractor(BaseBlockExtractor):
    """Heater 加热器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "outlet_stream_temperature": HeaterExtractor.get_prop(tree, fr"{base}\TEMP"),
            "comp_nums": comp_count,
            "outlet_pressure": HeaterExtractor.get_prop(tree, fr"{base}\PRES"),
        }
