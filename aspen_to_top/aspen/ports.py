from typing import Callable, Dict, List, Tuple


PortList = List[Dict[str, str]]
TopologyRegistrar = Callable[[str, str, str], None]


def extract_block_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    """Extract ToP-facing input/output port mappings for one Aspen block."""
    parser = PORT_PARSERS.get(block_type, parse_default_ports)
    return parser(tree, block_name, block_type, ports, register_topology)


def parse_default_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    inputs: PortList = []
    outputs: PortList = []

    add_indexed_inputs(inputs, ports, "F(IN)", "inlet_{}", block_name, register_topology)
    add_outputs(outputs, ports, "VD(OUT)", "top_vapor_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "B(OUT)", "bottom_liquid_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "LD(OUT)", "top_liquid_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "V(OUT)", "vapor_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "L(OUT)", "liquid_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "P(OUT)", "outlet_0", block_name, register_topology)
    add_outputs(outputs, ports, "H(OUT)", "hot_stream_outlet_0", block_name, register_topology)
    add_outputs(outputs, ports, "C(OUT)", "cold_stream_outlet_0", block_name, register_topology)
    add_outputs(inputs, ports, "H(IN)", "hot_stream_inlet_0", block_name, register_topology, direction="dest")
    add_outputs(inputs, ports, "C(IN)", "cold_stream_inlet_0", block_name, register_topology, direction="dest")

    return inputs, outputs


def parse_mixer_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    inputs, outputs = parse_default_ports(tree, block_name, block_type, ports, register_topology)
    inputs = []
    add_indexed_inputs(inputs, ports, "F(IN)", "inlet_{}", block_name, register_topology)
    return inputs, outputs


def parse_column_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    inputs: PortList = []
    outputs: PortList = []

    add_indexed_inputs(inputs, ports, "F(IN)", "feed_in_{}", block_name, register_topology)
    add_outputs(outputs, ports, "VD(OUT)", "top_vapor_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "B(OUT)", "bottom_liquid_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "LD(OUT)", "top_liquid_out_0", block_name, register_topology)
    add_column_side_draw_outputs(tree, outputs, ports, block_name, register_topology)

    return inputs, outputs


def parse_multi_product_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    inputs, outputs = parse_default_ports(tree, block_name, block_type, ports, register_topology)
    outputs = [port for port in outputs if "outlet_0" not in port]
    add_indexed_outputs(outputs, ports, "P(OUT)", "outlet_{}", block_name, register_topology)
    return inputs, outputs


def add_indexed_inputs(result: PortList, ports, aspen_port: str, top_port_pattern: str, block_name: str, register_topology: TopologyRegistrar) -> None:
    node = ports.FindNode(aspen_port)
    if not node:
        return
    for idx, port in enumerate(node.Elements):
        stream_name = port.Value
        result.append({top_port_pattern.format(idx): stream_name})
        register_topology(stream_name, "dest", block_name)


def add_indexed_outputs(result: PortList, ports, aspen_port: str, top_port_pattern: str, block_name: str, register_topology: TopologyRegistrar) -> None:
    node = ports.FindNode(aspen_port)
    if not node:
        return
    for idx, port in enumerate(node.Elements):
        stream_name = port.Value
        result.append({top_port_pattern.format(idx): stream_name})
        register_topology(stream_name, "source", block_name)


def add_outputs(
    result: PortList,
    ports,
    aspen_port: str,
    top_port: str,
    block_name: str,
    register_topology: TopologyRegistrar,
    direction: str = "source",
) -> None:
    node = ports.FindNode(aspen_port)
    if not node:
        return
    for port in node.Elements:
        stream_name = port.Value
        result.append({top_port: stream_name})
        register_topology(stream_name, direction, block_name)


def add_column_side_draw_outputs(tree, result: PortList, ports, block_name: str, register_topology: TopologyRegistrar) -> None:
    out_sp = ports.FindNode("SP(OUT)")
    if not out_sp:
        return

    stream_phase = {}
    prod_phase = tree.FindNode(fr"\Data\Blocks\{block_name}\Input\PROD_PHASE")
    if prod_phase:
        for port in prod_phase.Elements:
            stream_phase[port.Name] = port.Value

    for port in out_sp.Elements:
        stream_name = port.Value
        if stream_phase.get(stream_name) == "L":
            result.append({"liquid_side_draw_0": stream_name})
        else:
            result.append({"vapor_side_draw_0": stream_name})
        register_topology(stream_name, "source", block_name)


PORT_PARSERS = {
    "Mixer": parse_mixer_ports,
    "RadFrac": parse_column_ports,
    "SSplit": parse_multi_product_ports,
    "FSplit": parse_multi_product_ports,
    "Sep": parse_multi_product_ports,
}
