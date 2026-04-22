import json
import uuid
from typing import Any, Dict, List

from .property_fillers import fill_block_properties
from .templates import TemplateLoader


class GraphBuilder:
    """Build ToP process graph, nodes, edges, and source/sink node properties."""

    def __init__(self, template_loader: TemplateLoader, id_map: Dict[str, str]):
        self.template_loader = template_loader
        self.id_map = id_map

    def create_process_graph(self, input_data: Dict[str, Any], project_id: str, process_id: str) -> Dict[str, Any]:
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
        edges = []

        for connect_info in self.extract_connections(input_data["blocks"]):
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
        block_type = block_info["type"]

        node_props = self.template_loader.load_node_properties(block_type)
        node_data = self.template_loader.load_process_node(block_type)

        node_props = fill_block_properties(block_name, block_info, node_props)
        node_data["nodeProperties"] = json.dumps(node_props, ensure_ascii=False)
        node_data["id"] = self.id_map[block_name]

        for node in input_data.get("processGraph", {}).get("nodes", []):
            if block_name == node.get("id"):
                node_data["x"] = node.get("x", 0)
                node_data["y"] = node.get("y", 0)
                break

        node_data["data"]["label"] = block_name
        return node_data

    def create_stream_node(self, stream_name: str, stream_info: Dict[str, Any], node: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
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
        mole_fracs = list(stream_info.get("composition_mole_frac", {}).values())
        node_props["molar_compositions"]["value"] = mole_fracs
        node_props["molar_compositions"]["rowHeader"] = input_data["components"]["top_name"]
        node_props["molar_compositions"]["rows"] = input_data["components"]["top_name"]

        mole_flow = stream_info.get("properties", {}).get("mole_flow", {})
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
