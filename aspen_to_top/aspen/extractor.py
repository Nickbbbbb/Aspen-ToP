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


# Aspen block type -> 对应设备参数提取器。
# 新增设备时，一般需要：
# 1. 在 aspen/blocks 下新增 Extractor；
# 2. 在这里注册 Aspen block type；
# 3. 在 converter/property_fillers.py 中注册 ToP nodeProperties 填充逻辑。
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
    """Aspen Tree 节点访问辅助类。

    Aspen COM Tree 的读取方式是 tree.FindNode(path)，常见返回值：

    - node.Value: 当前节点值。
    - node.Elements: 子节点集合。
    - node.UnitString: Aspen 中该值的单位。

    这里把异常吞掉并返回 None/默认单位，是为了让某些 Aspen 文件缺字段时
    不至于中断整个转换流程。
    """

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
    """Aspen 数据提取器主类。

    本类负责把 Aspen COM Tree 转换为“标准化 Aspen JSON”。
    它不关心 ToP 模板长什么样，只输出稳定的中间结构：

    {
      "components": ...,
      "blocks": ...,
      "streams": ...,
      "methad": ...,
      "stream_topology_map": ...
    }

    其中 blocks 里每个设备会包含：

    - type: Aspen block type，例如 Flash2、Pump、RadFrac。
    - in_streams/out_streams: ToP 端口名到 Aspen 流股名的映射。
    - params: 设备参数，由 aspen/blocks/*.py 中的具体 Extractor 读取。
    """

    def __init__(self, tree, bkp_path: str):
        self.tree = tree
        self.bkp_path = bkp_path
        self.stream_topology_map = {}
        self.components_list = []
        self.tree_helper = TreeHelper

    def _register_topology(self, stream_name, source=None, dest=None):
        # 记录流股来源和去向，供调试和后续拓扑判断使用。
        # source/dest 都是 Aspen block name。
        if stream_name not in self.stream_topology_map:
            self.stream_topology_map[stream_name] = {"source": None, "dest": None}
        if source:
            self.stream_topology_map[stream_name]["source"] = source
        if dest:
            self.stream_topology_map[stream_name]["dest"] = dest

    def _register_port_topology(self, stream_name: str, direction: str, block_name: str):
        # ports.py 中端口解析函数只知道 direction 是 source/dest，
        # 这里把它转换成 stream_topology_map 需要的字段。
        if direction == "source":
            self._register_topology(stream_name, source=block_name)
        elif direction == "dest":
            self._register_topology(stream_name, dest=block_name)

    def extract_components(self) -> Dict[str, List]:
        """读取 Aspen 组分列表。

        主要读取路径：

        - \\Data\\Components\\Specifications\\Input\\ANAME: 分子式/组分标识。
        - \\Data\\Components\\Specifications\\Input\\CASN: CAS 号。
        - \\Data\\Components\\Specifications\\Input\\DBNAME: Aspen 数据库名称。

        后续 ToP 模板按 CAS 号加载组分模板，所以 CAS 是关键字段。
        """
        from ..utils.chemical_mapper import ChemicalMapper

        components_fenzi = self.tree.FindNode(r"\Data\Components\Specifications\Input\ANAME")
        components_cas = self.tree.FindNode(r"\Data\Components\Specifications\Input\CASN")
        components_name = self.tree.FindNode(r"\Data\Components\Specifications\Input\DBNAME")

        if components_fenzi:
            # Aspen 流股组成路径使用的是组分标签（节点名），例如 PROP、IBUT；
            # 不是 ANAME 中的分子式值，例如 C3H8、C4H10-2。
            self.components_list = [c.Name for c in components_fenzi.Elements]

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
        """读取 Aspen Blocks。

        每个 Block 分两步处理：

        1. ports.py 读取 Ports，得到 in_streams/out_streams。
        2. BLOCK_EXTRACTORS 根据 block_type 读取设备参数。

        这样端口规则和设备参数规则相互独立，后续维护成本较低。
        """
        blocks_root = self.tree.FindNode(r"\Data\Blocks")
        result = {}

        if not blocks_root:
            return result

        for block in blocks_root.Elements:
            b_name = block.Name
            # AttributeValue(6) 是 Aspen COM 中获取 block 类型的常见方式。
            # 例如 Flash2、RadFrac、Pump。
            block_type = block.AttributeValue(6)
            ports = block.FindNode("Ports")

            inputs = []
            outputs = []

            if ports:
                # 端口解析会把 Aspen 端口名 F(IN)、P(OUT)、V(OUT) 等
                # 转成 ToP 虚拟端口名 inlet_0、outlet_0、vapor_out_0 等。
                inputs, outputs = extract_block_ports(
                    self.tree, b_name, block_type, ports, self._register_port_topology
                )

            extractor_class = BLOCK_EXTRACTORS.get(block_type)
            if extractor_class:
                # 设备参数读取器只负责当前设备自己的 Input 参数。
                # outputs 会传进去，是因为某些设备如 Column 需要根据出口流股判断侧线信息。
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
        """读取 Aspen Streams。

        主要读取每条流股的：

        - 连接信息：Inventory/Streams 下的 Source/Destination。
        - 温度、压力、汽化率、质量流量、摩尔流量。
        - 各组分摩尔流量或组成相关值。

        这些信息主要用于 ToP Source 节点的入口条件。
        """
        streams_root = self.tree.FindNode(r"\Data\Streams")
        inventory_root = self.tree.FindNode(r"\Data\Flowsheet\Inventory\Streams")
        result = {}

        if not streams_root:
            return result

        for strm in streams_root.Elements:
            s_name = strm.Name
            # Aspen 中流股输入条件集中在 \Data\Streams\<stream>\Input 下。
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
        """读取 Aspen 全局物性方法，例如 SRK、PENG-ROB、UNIFAC。"""
        methad_node = self.tree.FindNode(r"\Data\Properties\Specifications\Input\GBASEOPSET")
        return methad_node.Value if methad_node else ""

    def extract_all(self) -> Dict[str, Any]:
        """执行完整 Aspen 数据提取。

        注意 processGraph 的几何坐标不在这里生成，而是在 main.py 中结合 .bkp
        原文读取坐标后补入。
        """
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
