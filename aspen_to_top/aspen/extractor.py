from typing import Dict, Any, List
from .blocks.flash import FlashExtractor
from .blocks.heater import HeaterExtractor
from .blocks.compressor import CompressorExtractor
from .blocks.pump import PumpExtractor
from .blocks.valve import ValveExtractor
from .blocks.mixer import MixerExtractor
from .blocks.splitter import SplitterExtractor
from .blocks.heatx import HeatXExtractor
from .blocks.column import ColumnExtractor
from .blocks.component_splitter import ComponentSplitterExtractor
from .blocks.recycle_breaker import RecycleBreakerExtractor
from .blocks.rstoic import RStoicExtractor
from .ports import extract_block_ports


BLOCK_EXTRACTORS = {
    "Flash2": FlashExtractor,
    "Heater": HeaterExtractor,
    "Compr": CompressorExtractor,
    "Pump": PumpExtractor,
    "Valve": ValveExtractor,
    "Mixer": MixerExtractor,
    "SSplit": SplitterExtractor,
    "FSplit": SplitterExtractor,
    "HeatX": HeatXExtractor,
    "RadFrac": ColumnExtractor,
    "Sep": ComponentSplitterExtractor,
    "RecycleBreaker": RecycleBreakerExtractor,
    "RStoic": RStoicExtractor,
}


class TreeHelper:
    """树节点访问辅助类"""

    @staticmethod
    def get_val(tree, path: str):
        try:
            node = tree.FindNode(path)
            return node.Value if node else None
        except:
            return None

    @staticmethod
    def get_prop_with_unit(tree, path: str, default_unit: str = "") -> Dict[str, Any]:
        try:
            node = tree.FindNode(path)
            if node:
                unit = getattr(node, "UnitString", default_unit)
                val = node.Value
                if val is None:
                    val = 0.0
                return {"value": val, "unit": unit}
            else:
                return {"value": None, "unit": default_unit}
        except Exception:
            return {"value": None, "unit": default_unit}


class AspenExtractor:
    """Aspen 数据提取器主类"""

    def __init__(self, tree, bkp_path: str):
        self.tree = tree
        self.bkp_path = bkp_path
        self.stream_topology_map = {}
        self.components_list = []
        self.tree_helper = TreeHelper

    def _register_topology(self, stream_name, source=None, dest=None):
        if stream_name not in self.stream_topology_map:
            self.stream_topology_map[stream_name] = {"source": None, "dest": None}
        if source:
            self.stream_topology_map[stream_name]["source"] = source
        if dest:
            self.stream_topology_map[stream_name]["dest"] = dest

    def _register_port_topology(self, stream_name: str, direction: str, block_name: str):
        if direction == "source":
            self._register_topology(stream_name, source=block_name)
        elif direction == "dest":
            self._register_topology(stream_name, dest=block_name)

    def extract_components(self) -> Dict[str, List]:
        from ..utils.chemical_mapper import ChemicalMapper

        components_fenzi = self.tree.FindNode(r"\Data\Components\Specifications\Input\ANAME")
        components_cas = self.tree.FindNode(r"\Data\Components\Specifications\Input\CASN")
        components_name = self.tree.FindNode(r"\Data\Components\Specifications\Input\DBNAME")

        if components_fenzi:
            self.components_list = [c.Value for c in components_fenzi.Elements]

        result = {
            "fenzi": [c.Value for c in components_fenzi.Elements] if components_fenzi else [],
            "label": [c.Name for c in components_fenzi.Elements] if components_fenzi else [],
            "cas": [c.Value for c in components_cas.Elements] if components_cas else [],
            "aspen_name": [c.Value for c in components_name.Elements] if components_name else [],
        }

        result["top_name"] = [
            ChemicalMapper.get_local_name_by_aspen(name) for name in result["aspen_name"]
        ]

        return result

    def extract_blocks(self, components_data: Dict) -> Dict[str, Dict]:
        blocks_root = self.tree.FindNode(r"\Data\Blocks")
        result = {}

        if not blocks_root:
            return result

        for block in blocks_root.Elements:
            b_name = block.Name
            block_type = block.AttributeValue(6)
            ports = block.FindNode("Ports")

            inputs = []
            outputs = []

            if ports:
                inputs, outputs = extract_block_ports(
                    self.tree, b_name, block_type, ports, self._register_port_topology
                )

            extractor_class = BLOCK_EXTRACTORS.get(block_type)
            if extractor_class:
                params = extractor_class.extract(
                    self.tree, b_name, len(components_data.get("top_name", [])), outputs, block_type
                )
            else:
                params = {"comp_nums": len(components_data.get("top_name", []))}

            result[b_name] = {
                "type": block_type,
                "in_streams": inputs,
                "out_streams": outputs,
                "params": params
            }

        return result

    def extract_streams(self) -> Dict[str, Dict]:
        streams_root = self.tree.FindNode(r"\Data\Streams")
        inventory_root = self.tree.FindNode(r"\Data\Flowsheet\Inventory\Streams")
        result = {}

        if not streams_root:
            return result

        for strm in streams_root.Elements:
            s_name = strm.Name
            base = fr"\Data\Streams\{s_name}\Input"

            inv_node = inventory_root.FindNode(s_name) if inventory_root else None
            source = None
            dest = None
            if inv_node:
                source_node = inv_node.FindNode("Source")
                dest_node = inv_node.FindNode("Destination")
                source = source_node.Value if source_node else None
                dest = dest_node.Value if dest_node else None

            strm_data = {
                "connection": {"from": source, "to": dest},
                "properties": {
                    "temperature": self.tree_helper.get_prop_with_unit(self.tree, fr"{base}\TEMP\MIXED"),
                    "pressure": self.tree_helper.get_prop_with_unit(self.tree, fr"{base}\PRES\MIXED"),
                    "vapor_frac": self.tree_helper.get_prop_with_unit(self.tree, fr"{base}\RES_VFRAC"),
                    "mass_flow": self.tree_helper.get_prop_with_unit(self.tree, fr"{base}\MASSFLMX\MIXED"),
                    "mole_flow": self.tree_helper.get_prop_with_unit(self.tree, fr"{base}\TOTFLOW\MIXED"),
                },
                "composition_mole_frac": {}
            }

            for comp_id in self.components_list:
                val = self.tree_helper.get_val(self.tree, fr"{base}\FLOW\MIXED\{comp_id}")
                strm_data["composition_mole_frac"][comp_id] = val if val is not None else 0.0

            result[s_name] = strm_data

        return result

    def extract_method(self) -> str:
        methad_node = self.tree.FindNode(r"\Data\Properties\Specifications\Input\GBASEOPSET")
        return methad_node.Value if methad_node else ""

    def extract_all(self) -> Dict[str, Any]:
        print("正在提取物理属性数据...")
        components = self.extract_components()
        blocks = self.extract_blocks(components)
        streams = self.extract_streams()
        method = self.extract_method()

        return {
            "components": components,
            "blocks": blocks,
            "streams": streams,
            "params": {},
            "methad": method,
            "stream_topology_map": self.stream_topology_map
        }
