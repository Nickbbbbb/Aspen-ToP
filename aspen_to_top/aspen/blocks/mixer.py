from typing import Dict, Any, List
from .base import BaseBlockExtractor


class MixerExtractor(BaseBlockExtractor):
    """Mixer 混合器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        no_inlets = 0
        in_nodes = tree.FindNode(fr"\Data\Blocks\{block_name}\Ports\F(IN)")
        if in_nodes:
            no_inlets = len(list(in_nodes.Elements))

        return {
            "outlet_pressure": MixerExtractor.get_prop(tree, fr"{base}\PRES"),
            "comp_nums": comp_count,
            "no_inlets": no_inlets,
        }
