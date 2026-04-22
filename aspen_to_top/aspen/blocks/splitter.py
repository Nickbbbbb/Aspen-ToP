from typing import Dict, Any, List
from .base import BaseBlockExtractor


class SplitterExtractor(BaseBlockExtractor):
    """SSplit/FSplit 分流器提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "SSplit") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"
        no_outlets = 0
        out_nodes = tree.FindNode(fr"\Data\Blocks\{block_name}\Ports\P(OUT)")
        if out_nodes:
            no_outlets = len(list(out_nodes.Elements))

        split_fraction_value = []
        split_fraction_rows = []
        split_fraction_rowHeader = []
        index = 0
        current_FRAC = 0

        frac_node = tree.FindNode(fr"{base}\FRAC")
        if frac_node:
            for out_streams in frac_node.Elements:
                if block_type == "FSplit":
                    FRAC_node = tree.FindNode(fr"{base}\FRAC\{out_streams.Name}")
                    if FRAC_node and FRAC_node.Value:
                        value = FRAC_node.Value
                        current_FRAC += value
                    else:
                        value = 1 - current_FRAC
                else:
                    value = tree.FindNode(fr"{base}\FRAC\{out_streams.Name}\MIXED").Value

                split_fraction_rows.append(out_streams.Name)
                split_fraction_value.append(value)
                split_fraction_rowHeader.append(f"outlet_{index}")
                index += 1

        return {
            "outlet_pressure": SplitterExtractor.get_prop(tree, fr"{base}\PRES"),
            "comp_nums": comp_count,
            "no_outlets": no_outlets,
            "split_fraction_value": split_fraction_value,
            "split_fraction_rows": split_fraction_rows,
            "split_fraction_rowHeader": split_fraction_rowHeader,
        }


class SSplitExtractor(SplitterExtractor):
    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "SSplit") -> Dict[str, Any]:
        return SplitterExtractor.extract(tree, block_name, comp_count, outputs, "SSplit")


class FSplitExtractor(SplitterExtractor):
    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "FSplit") -> Dict[str, Any]:
        return SplitterExtractor.extract(tree, block_name, comp_count, outputs, "FSplit")
