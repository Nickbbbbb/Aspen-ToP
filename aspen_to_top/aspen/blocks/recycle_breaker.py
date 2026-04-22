from typing import Dict, Any, List
from .base import BaseBlockExtractor


class RecycleBreakerExtractor(BaseBlockExtractor):
    """RecycleBreaker 循环切断器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        return {
            "comp_nums": comp_count,
        }
