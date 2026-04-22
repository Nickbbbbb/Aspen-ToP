from typing import Dict, Any, List
from .base import BaseBlockExtractor


class CompressorExtractor(BaseBlockExtractor):
    """Compr 压缩机提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        return {
            "outlet_stream_pressure": CompressorExtractor.get_prop(tree, fr"{base}\PRES"),
            "comp_nums": comp_count,
            "isentropic_efficiency": CompressorExtractor.get_prop(tree, fr"{base}\SEFF"),
            "mechanical_efficiency": CompressorExtractor.get_prop(tree, fr"{base}\MEFF"),
        }
