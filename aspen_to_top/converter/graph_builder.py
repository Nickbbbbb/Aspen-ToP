import json
import uuid
from typing import Any, Dict, List

from .property_fillers import fill_block_properties
from .templates import TemplateLoader


class GraphBuilder:
    """构建 ToP 流程图。

    ToP 把流程图存放在 omProcessGraph 中，其中：

    - processNodes 是一个 JSON 字符串，内容是节点数组。
    - processEdges 是一个 JSON 字符串，内容是边数组。

    注意它们不是普通 list，而是“序列化后的 JSON 字符串”，所以这里最后会
    json.dumps(edges/nodes) 再写入 omProcessGraph。
    """

    def __init__(self, template_loader: TemplateLoader, id_map: Dict[str, str]):
        self.template_loader = template_loader
        self.id_map = id_map

    def create_process_graph(self, input_data: Dict[str, Any], project_id: str, process_id: str) -> Dict[str, Any]:
        """构建 omProcessGraph 整体结构。"""
        edges = self.create_edges(input_data)
        nodes = self.create_nodes(input_data)

        return {
            "createBy": "admin",
            "createTime": "2026-01-30 06:12:16",
            "delFlag": "0",
            "graphType": 1,
            "id": process_id,
            "processEdges": json.dumps(edges, ensure_ascii=False),
            "processNodes": json.dumps(nodes, ensure_ascii=False),
            "projectId": project_id,
            "updateBy": "admin",
            "updateTime": "2026-01-30 06:12:16"
        }

    def create_edges(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据 blocks 中的 in_streams/out_streams 构建 ToP 边。

        每条边的关键字段：

        - attrs.label: Aspen 流股名，如 S1。
        - source.cell: 来源节点 ToP ID。
        - source.port: 来源 ToP 端口名。
        - target.cell: 目标节点 ToP ID。
        - target.port: 目标 ToP 端口名。
        """
        edges = []

        for connect_info in self.extract_connections(input_data["blocks"]):
            # 每条边都从模板深拷贝出来，避免多条边共享同一个 dict。
            edge = self.template_loader.load_process_edge_template()
            edge["id"] = f"{uuid.uuid4()}_s-{len(edges) + 1}"
            edge["attrs"]["label"] = connect_info["connect"]
            edge["source"]["cell"] = self.id_map.get(connect_info["from"], connect_info["from"])
            edge["source"]["port"] = connect_info["from_port"]
            edge["target"]["cell"] = self.id_map.get(connect_info["to"], connect_info["to"])
            edge["target"]["port"] = connect_info["to_port"]
            edges.append(edge)

        return edges

    def extract_connections(self, blocks_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从标准化 blocks 中抽取 stream 连接关系。

        输入来自 AspenExtractor.extract_blocks()：

        block["in_streams"]  = [{"inlet_0": "S1"}]
        block["out_streams"] = [{"vapor_out_0": "S2"}]

        本函数会反向整理成以 stream 为中心的连接：

        S1: source=Source节点, target=某设备 inlet_0
        S2: source=某设备 vapor_out_0, target=Sink节点
        """
        connections = []
        stream_sources = {}
        stream_destinations = {}

        for module_name, module_info in blocks_data.items():
            for in_port_dict in module_info.get("in_streams", []):
                for port_name, stream_name in in_port_dict.items():
                    if stream_name not in stream_destinations:
                        stream_destinations[stream_name] = []
                    stream_destinations[stream_name].append((module_name, port_name))

            for out_port_dict in module_info.get("out_streams", []):
                for port_name, stream_name in out_port_dict.items():
                    if stream_name not in stream_sources:
                        stream_sources[stream_name] = []
                    stream_sources[stream_name].append((module_name, port_name))

        # 一个 stream 可能只有来源或只有去向：
        # - 只有去向：外部进料，起点是 Source 节点。
        # - 只有来源：外部产品，终点是 Sink 节点。
        all_streams = set(stream_sources.keys()) | set(stream_destinations.keys())

        for stream in all_streams:
            connection = {"connect": stream}

            if stream in stream_sources:
                from_module, from_port = stream_sources[stream][0]
                connection["from"] = from_module
                connection["from_port"] = from_port
            else:
                connection["from"] = stream
                connection["from_port"] = "outlet_0"

            if stream in stream_destinations:
                to_module, to_port = stream_destinations[stream][0]
                connection["to"] = to_module
                connection["to_port"] = to_port
            else:
                connection["to"] = stream
                connection["to_port"] = "inlet_0"

            connections.append(connection)

        return connections

    def create_nodes(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建 ToP 节点数组。

        节点分两类：

        1. Aspen Blocks -> ToP 设备节点。
        2. processGraph 中标记为 Source/Sink 的 Streams -> ToP Source/Sink 节点。
        """
        nodes = []

        for block_name, block_info in input_data["blocks"].items():
            node_data = self.create_block_node(block_name, block_info, input_data)
            if node_data:
                nodes.append(node_data)

        graph_nodes = input_data.get("processGraph", {}).get("nodes", [])
        for stream_name, stream_info in input_data.get("streams", {}).items():
            for node in graph_nodes:
                if stream_name == node.get("id"):
                    node_data = self.create_stream_node(stream_name, stream_info, node, input_data)
                    if node_data:
                        nodes.append(node_data)
                    break

        return nodes

    def create_block_node(self, block_name: str, block_info: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建设备节点。

        设备节点由两份模板组成：

        - processNodes_<type>.json: 节点外观、端口、宽高等。
        - <type>_properties.json: nodeProperties 参数表。

        设备参数填充由 property_fillers.py 负责。
        """
        block_type = block_info["type"]

        node_props = self.template_loader.load_node_properties(block_type)
        node_data = self.template_loader.load_process_node(block_type)

        # 把 Aspen 参数映射到 ToP nodeProperties。
        node_props = fill_block_properties(block_name, block_info, node_props)
        self.sync_dynamic_ports(node_data, block_info)
        node_data["nodeProperties"] = json.dumps(node_props, ensure_ascii=False)
        node_data["id"] = self.id_map[block_name]

        for node in input_data.get("processGraph", {}).get("nodes", []):
            if block_name == node.get("id"):
                node_data["x"] = node.get("x", 0)
                node_data["y"] = node.get("y", 0)
                break

        node_data["data"]["label"] = block_name
        return node_data

    def sync_dynamic_ports(self, node_data: Dict[str, Any], block_info: Dict[str, Any]) -> None:
        """根据实际 Aspen 端口数量重建 ToP 节点虚拟端口。

        ToP 的 processNode 模板里会带一些示例端口，但这些端口不一定和当前
        Aspen 文件一致。尤其是 RadFrac：边构建阶段会引用 feed_in_0，
        如果节点模板里只有 feed_in_1/feed_in_2，ToP 导入时连接就会断。
        """
        block_type = block_info.get("type")
        if block_type == "RadFrac":
            self.sync_column_ports(node_data, block_info)

    def sync_column_ports(self, node_data: Dict[str, Any], block_info: Dict[str, Any]) -> None:
        """重建精馏塔 feed/side draw 虚拟端口。

        这里沿用旧代码的 ToP 端口习惯：即使只有 1 个实际进料，也保留
        feed_in_0 和一个额外虚拟桩 feed_in_1。侧线端口同理，至少保留
        *_side_draw_0，实际有 N 条侧线时保留 0..N。
        """
        params = block_info.get("params", {})
        feed_count = len(block_info.get("in_streams", []))
        vapor_count = len(params.get("vapor_side_draw", {}).get("stream_name", []))
        liquid_count = len(params.get("liquid_side_draw", {}).get("stream_name", []))

        self.replace_virtual_ports(node_data, "feed_in", "feed_in", feed_count + 1, first_name="feed_in")
        self.replace_virtual_ports(node_data, "vapor_side_draw", "vapor_side_draw", vapor_count + 1, first_name="虚拟桩")
        self.replace_virtual_ports(node_data, "liquid_side_draw", "liquid_side_draw", liquid_count + 1, first_name="liquid_side_draw")

    def replace_virtual_ports(
        self,
        node_data: Dict[str, Any],
        group_name: str,
        port_prefix: str,
        count: int,
        first_name: str,
    ) -> None:
        """替换某个端口组的 relateVirtualPortList，确保编号从 0 开始。"""
        count = max(count, 1)
        for port_group in node_data.get("ports", []):
            if port_group.get("name") != group_name:
                continue

            related_entity_id = port_group.get("id", "")
            related_entity_name = port_group.get("name", group_name)
            virtual_ports = []
            for index in range(count):
                virtual_ports.append({
                    "id": f"{port_prefix}_{index}",
                    "name": first_name if index == 0 else "虚拟桩",
                    "relatedEntityId": related_entity_id,
                    "relatedEntityName": related_entity_name,
                })
            port_group["relateVirtualPortList"] = virtual_ports
            return

    def create_stream_node(self, stream_name: str, stream_info: Dict[str, Any], node: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建 Source/Sink 节点。

        Source 节点需要把 Aspen stream 的温度、压力、流量、组成写入属性；
        Sink 节点通常只需要模板默认属性。
        """
        node_type = node.get("type", "Source")

        if node_type == "Sink":
            node_props = self.template_loader.load_node_properties("Sink")
            node_data = self.template_loader.load_process_node("Sink")
            node_props = self.fill_sink_properties(node_props)
        elif node_type == "Source":
            node_props = self.template_loader.load_node_properties("Source")
            node_data = self.template_loader.load_process_node("Source")
            node_props = self.fill_source_properties(node_props, stream_info, input_data)
        else:
            return None

        node_data["nodeProperties"] = json.dumps(node_props, ensure_ascii=False)
        node_data["id"] = self.id_map.get(stream_name, stream_name)
        node_data["x"] = node.get("x", 0)
        node_data["y"] = node.get("y", 0)
        node_data["data"]["label"] = stream_name
        return node_data

    def fill_sink_properties(self, node_props: Dict[str, Any]) -> Dict[str, Any]:
        return node_props

    def fill_source_properties(self, node_props: Dict[str, Any], stream_info: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """把 Aspen 进料流股条件写入 ToP Source 节点属性。"""
        mole_fracs = list(stream_info.get("composition_mole_frac", {}).values())
        node_props["molar_compositions"]["value"] = mole_fracs
        node_props["molar_compositions"]["rowHeader"] = input_data["components"]["top_name"]
        node_props["molar_compositions"]["rows"] = input_data["components"]["top_name"]

        mole_flow = stream_info.get("properties", {}).get("mole_flow", {})
        # Aspen 有时返回 kmol/sec；ToP 侧这里期望 mol/s，所以做一次换算。
        if mole_flow.get("unit") == "kmol/sec":
            node_props["molar_flowrate"]["value"] = mole_flow.get("value", 0) * 1000
        else:
            unit = mole_flow.get("unit", "kmol/s")
            if "sec" in unit:
                unit = unit.replace("sec", "s")
            node_props["molar_flowrate"]["value"] = mole_flow.get("value", 0)
            node_props["molar_flowrate"]["unit"] = unit

        pressure = stream_info.get("properties", {}).get("pressure", {})
        node_props["pressure"]["value"] = pressure.get("value")
        node_props["pressure"]["unit"] = pressure.get("unit", "")

        temperature = stream_info.get("properties", {}).get("temperature", {})
        node_props["temperature"]["value"] = temperature.get("value")
        node_props["temperature"]["unit"] = temperature.get("unit", "")

        node_props["comp_num"]["value"] = len(mole_fracs)
        return node_props
