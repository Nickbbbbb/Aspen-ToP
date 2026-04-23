from typing import Callable, Dict, List, Tuple


PortList = List[Dict[str, str]]
TopologyRegistrar = Callable[[str, str, str], None]


def extract_block_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    """提取某个 Aspen Block 的端口映射。

    Aspen 的端口名和 ToP 的端口名不是一一同名的，例如：

    - Aspen F(IN) -> ToP inlet_0/feed_in_0
    - Aspen V(OUT) -> ToP vapor_out_0
    - Aspen L(OUT) -> ToP liquid_out_0
    - Aspen P(OUT) -> ToP outlet_0/outlet_1/...

    不同设备的端口规则不同，所以这里通过 PORT_PARSERS 注册表分发。
    返回值是 (inputs, outputs)，格式示例：

    inputs = [{"inlet_0": "S1"}]
    outputs = [{"vapor_out_0": "S2"}, {"liquid_out_0": "S3"}]
    """
    parser = PORT_PARSERS.get(block_type, parse_default_ports)
    return parser(tree, block_name, block_type, ports, register_topology)


def parse_default_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    """默认设备端口规则。

    适用于大部分一进一出或标准汽/液出口设备。
    特殊设备如 Mixer、RadFrac、Splitter 会覆盖此规则。
    """
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
    """Mixer 端口规则。

    Mixer 允许多个 F(IN)，所以输入端口要编号为 inlet_0、inlet_1...
    输出端口仍沿用默认规则。
    """
    inputs, outputs = parse_default_ports(tree, block_name, block_type, ports, register_topology)
    inputs = []
    add_indexed_inputs(inputs, ports, "F(IN)", "inlet_{}", block_name, register_topology)
    return inputs, outputs


def parse_column_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    """RadFrac 精馏塔端口规则。

    塔的进料口使用 feed_in_0、feed_in_1...
    顶/底产品使用 top_vapor_out_0、bottom_liquid_out_0 等。
    侧线产品需要结合 PROD_PHASE 判断是液相侧线还是汽相侧线。
    """
    inputs: PortList = []
    outputs: PortList = []

    add_indexed_inputs(inputs, ports, "F(IN)", "feed_in_{}", block_name, register_topology)
    add_outputs(outputs, ports, "VD(OUT)", "top_vapor_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "B(OUT)", "bottom_liquid_out_0", block_name, register_topology)
    add_outputs(outputs, ports, "LD(OUT)", "top_liquid_out_0", block_name, register_topology)
    add_column_side_draw_outputs(tree, outputs, ports, block_name, register_topology)

    return inputs, outputs


def parse_multi_product_ports(tree, block_name: str, block_type: str, ports, register_topology: TopologyRegistrar) -> Tuple[PortList, PortList]:
    """多出口设备端口规则。

    SSplit、FSplit、Sep 的 P(OUT) 可能有多个元素，需要映射为：
    outlet_0、outlet_1、outlet_2...
    """
    inputs, outputs = parse_default_ports(tree, block_name, block_type, ports, register_topology)
    outputs = [port for port in outputs if "outlet_0" not in port]
    add_indexed_outputs(outputs, ports, "P(OUT)", "outlet_{}", block_name, register_topology)
    return inputs, outputs


def add_indexed_inputs(result: PortList, ports, aspen_port: str, top_port_pattern: str, block_name: str, register_topology: TopologyRegistrar) -> None:
    """添加带序号的输入端口，并登记该流股的目标 block。"""
    node = ports.FindNode(aspen_port)
    if not node:
        return
    for idx, port in enumerate(node.Elements):
        stream_name = port.Value
        result.append({top_port_pattern.format(idx): stream_name})
        register_topology(stream_name, "dest", block_name)


def add_indexed_outputs(result: PortList, ports, aspen_port: str, top_port_pattern: str, block_name: str, register_topology: TopologyRegistrar) -> None:
    """添加带序号的输出端口，并登记该流股的来源 block。"""
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
    """添加不带序号的端口。

    direction=source 表示当前 block 是流股来源；
    direction=dest 表示当前 block 是流股目标。
    """
    node = ports.FindNode(aspen_port)
    if not node:
        return
    for port in node.Elements:
        stream_name = port.Value
        result.append({top_port: stream_name})
        register_topology(stream_name, direction, block_name)


def add_column_side_draw_outputs(tree, result: PortList, ports, block_name: str, register_topology: TopologyRegistrar) -> None:
    """读取 RadFrac 侧线出口。

    Aspen 的 SP(OUT) 只告诉我们有哪些侧线流股，具体是汽相还是液相要去
    \Data\Blocks\<block>\Input\PROD_PHASE 中按流股名查询。
    """
    out_sp = ports.FindNode("SP(OUT)")
    if not out_sp:
        return

    stream_phase = {}
    prod_phase = tree.FindNode(fr"\Data\Blocks\{block_name}\Input\PROD_PHASE")
    if prod_phase:
        for port in prod_phase.Elements:
            stream_phase[port.Name] = port.Value

    vapor_index = 0
    liquid_index = 0
    for port in out_sp.Elements:
        stream_name = port.Value
        if stream_phase.get(stream_name) == "L":
            result.append({f"liquid_side_draw_{liquid_index}": stream_name})
            liquid_index += 1
        else:
            result.append({f"vapor_side_draw_{vapor_index}": stream_name})
            vapor_index += 1
        register_topology(stream_name, "source", block_name)


# 特殊设备端口解析注册表。没有出现在这里的 block_type 会使用 parse_default_ports。
PORT_PARSERS = {
    "Mixer": parse_mixer_ports,
    "RadFrac": parse_column_ports,
    "SSplit": parse_multi_product_ports,
    "FSplit": parse_multi_product_ports,
    "Sep": parse_multi_product_ports,
}
