from typing import Dict, Any, List
from .base import BaseBlockExtractor


class ComponentSplitterExtractor(BaseBlockExtractor):
    """Sep 组分分离器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        no_outlets = 0
        out_nodes = tree.FindNode(fr"\Data\Blocks\{block_name}\Ports\P(OUT)")
        if out_nodes:
            no_outlets = len(list(out_nodes.Elements))

        split_fractions_value = []
        split_fractions_rows = []
        split_fractions_rowHeader = []
        split_fractions_cols = []
        split_fractions_colHeader = []
        index = 0

        fracs_node = tree.FindNode(fr"{base}\FRACS")
        if fracs_node:
            for out_stream in fracs_node.Elements:
                split_fractions_rowHeader.append(f"outlet_{index}")
                split_fractions_rows.append(out_stream.Name)
                index += 1
                comp_node = tree.FindNode(fr"{base}\FRACS\{out_stream.Name}\MIXED")
                if comp_node:
                    for comp in comp_node.Elements:
                        if comp.Name not in split_fractions_cols:
                            split_fractions_cols.append(comp.Name)
                            split_fractions_colHeader.append(comp.Name)
                        if comp.Value:
                            split_fractions_value.append(comp.Value)
                        else:
                            split_fractions_value.append(0)

        return {
            "comp_nums": comp_count,
            "no_outlets": no_outlets,
            "split_fractions_value": split_fractions_value,
            "split_fractions_rows": split_fractions_rows,
            "split_fractions_rowHeader": split_fractions_rowHeader,
            "split_fractions_cols": split_fractions_cols,
            "split_fractions_colHeader": split_fractions_colHeader,
        }
