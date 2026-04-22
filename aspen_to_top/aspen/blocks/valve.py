from typing import Dict, Any, List
from .base import BaseBlockExtractor


class ValveExtractor(BaseBlockExtractor):
    """Valve 阀门提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "comp_nums": comp_count,
            "outlet_pressure": ValveExtractor.get_prop(tree, fr"{base}\P_OUT"),
        }
