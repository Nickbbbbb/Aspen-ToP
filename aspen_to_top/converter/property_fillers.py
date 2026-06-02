from typing import Any, Callable, Dict


NodeProps = Dict[str, Any]
BlockInfo = Dict[str, Any]
PropertyFiller = Callable[[NodeProps, Dict[str, Any]], NodeProps]


def fill_block_properties(block_name: str, block_info: BlockInfo, node_props: NodeProps) -> NodeProps:
    """按 Aspen 设备类型把参数填入 ToP 节点属性模板。

    参数来源是 aspen/blocks/*.py 读取出的标准化 params；node_props 是
    Template/nodeProperties 下对应设备的模板。这里不读取 Aspen COM，也
    不创建节点 ID，只做字段级映射。
    """
    params = block_info.get("params", {})
    block_type = block_info["type"]
    filler = PROPERTY_FILLERS.get(block_type)
    if not filler:
        return node_props
    return filler(node_props, params)


def fill_flash(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Flash2 闪蒸罐参数。

    Aspen 的 SPEC_OPT 决定 ToP 的 Thermal_specification：
    TP 表示温度压力规格；PV 表示压力和汽化率规格。
    """
    node_props["system_pressure"]["value"] = params.get("system_pressure", {}).get("value")
    node_props["system_pressure"]["unit"] = params.get("system_pressure", {}).get("unit", "")
    spec_opt = params.get("SPEC_OPT", {}).get("value")
    if spec_opt == "TP":
        node_props["system_temperature"]["value"] = params.get("system_temperature", {}).get("value")
        node_props["system_temperature"]["unit"] = params.get("system_temperature", {}).get("unit", "")
        node_props["system_temperature"]["fixed"] = True
        node_props["Thermal_specification"]["value"] = "0"
    elif spec_opt == "PV":
        node_props["system_vapor_molar_fraction"]["value"] = params.get("system_vapor_molar_fraction", {}).get("value")
        node_props["system_vapor_molar_fraction"]["unit"] = "mol/mol"
        node_props["system_temperature"]["fixed"] = True
        node_props["Thermal_specification"]["value"] = "1"
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_heater(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Heater 加热器/冷却器参数。"""
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["outlet_stream_temperature"]["value"] = params.get("outlet_stream_temperature", {}).get("value")
    node_props["outlet_stream_temperature"]["unit"] = params.get("outlet_stream_temperature", {}).get("unit", "")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_pump(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Pump 参数。

    Aspen 的 OPT_SPEC=PRES 表示直接指定出口压力；DELP 表示指定压升。
    """
    opt_spec = params.get("OPT_SPEC", {}).get("value")
    if opt_spec == "PRES":
        node_props["outlet_specification"]["value"] = "0"
        node_props["outlet_stream_pressure"]["value"] = params.get("outlet_stream_pressure", {}).get("value")
        node_props["outlet_stream_pressure"]["unit"] = params.get("outlet_stream_pressure", {}).get("unit", "")
    elif opt_spec == "DELP":
        node_props["outlet_specification"]["value"] = "1"
        node_props["pressure_increase"]["value"] = params.get("pressure_increase", {}).get("value")
        node_props["pressure_increase"]["unit"] = params.get("pressure_increase", {}).get("unit", "")
    node_props["pumping_efficiency"]["value"] = params.get("pumping_efficiency", {}).get("value")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_mixer(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Mixer 参数，重点是出口压力和入口数量。"""
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["no_inlets"]["value"] = params.get("no_inlets", 0)
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_splitter(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充普通 Splitter 参数。

    SSplit 和 FSplit 目前共用该逻辑，差异由 Aspen 读取层整理到 params 中。
    """
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["no_outlets"]["value"] = params.get("no_outlets", 0)
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["split_fraction"]["value"] = params.get("split_fraction_value", [])
    node_props["split_fraction"]["rowHeader"] = params.get("split_fraction_rowHeader", [])
    return node_props


def fill_component_splitter(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Sep/ComponentSplitter 逐组分分割参数。"""
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["no_outlets"]["value"] = params.get("no_outlets", 0)
    node_props["split_fractions"]["value"] = params.get("split_fractions_value", [])
    node_props["split_fractions"]["rowHeader"] = params.get("split_fractions_rowHeader", [])
    node_props["split_fractions"]["colHeader"] = params.get("split_fractions_colHeader", [])
    node_props["split_fractions"]["cols"] = params.get("split_fractions_cols", [])
    return node_props


def fill_heatx(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 HeatX 换热器参数。

    ToP 单位字符串更偏向 W，Aspen 可能返回 Watt，因此这里做轻量替换。
    """
    node_props["hot_outlet_pressure"]["value"] = params.get("hot_outlet_pressure", {}).get("value")
    node_props["hot_outlet_pressure"]["unit"] = params.get("hot_outlet_pressure", {}).get("unit", "")
    node_props["cold_outlet_pressure"]["value"] = params.get("cold_outlet_pressure", {}).get("value")
    node_props["cold_outlet_pressure"]["unit"] = params.get("cold_outlet_pressure", {}).get("unit", "")
    node_props["area"]["value"] = params.get("area", {}).get("value")
    node_props["area"]["unit"] = params.get("area", {}).get("unit", "")
    node_props["u_overall"]["value"] = params.get("u_overall", {}).get("value")
    node_props["u_overall"]["unit"] = params.get("u_overall", {}).get("unit", "").replace("Watt", "W")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_compressor(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Compressor 压缩机参数。"""
    node_props["outlet_stream_pressure"]["value"] = params.get("outlet_stream_pressure", {}).get("value")
    node_props["outlet_stream_pressure"]["unit"] = params.get("outlet_stream_pressure", {}).get("unit", "")
    node_props["isentropic_efficiency"]["value"] = params.get("isentropic_efficiency", {}).get("value")
    node_props["mechanical_efficiency"]["value"] = params.get("mechanical_efficiency", {}).get("value")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_valve(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 Valve 阀门参数。"""
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    return node_props


def fill_column(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    """填充 RadFrac 精馏塔参数。

    精馏塔是当前最复杂的设备：除了塔板数、进料板、压力分布，还要处理
    冷凝器类型、侧线采出数量、回流比和塔顶流量初值。
    """
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["no_trays"]["value"] = params.get("no_trays", {}).get("value")
    node_props["no_total_trays"]["value"] = params.get("no_trays", {}).get("value")
    node_props["vapor_molar_composition_profile_guess"]["cloumnSize"] = params.get("no_trays", {}).get("value")
    node_props["liquid_molar_composition_profile_guess"]["cloumnSize"] = params.get("no_trays", {}).get("value")
    node_props["no_feeds"]["value"] = params.get("no_feeds", 0)
    node_props["feed_trays"]["value"] = params.get("feed_trays_value", [])
    node_props["feed_trays"]["rows"] = params.get("feed_trays_rows", [])
    node_props["feed_trays"]["rowSize"] = len(params.get("feed_trays_rows", []))
    node_props["feed_trays"]["rowHeader"] = params.get("feed_trays_rowHeader", [])

    vapor_draw = params.get("vapor_side_draw", {})
    liquid_draw = params.get("liquid_side_draw", {})
    node_props["no_vapor_side_draw"]["value"] = len(vapor_draw.get("stream_name", []))
    node_props["no_liquid_side_draw"]["value"] = len(liquid_draw.get("stream_name", []))
    fill_side_draw_properties(node_props, "vapor", vapor_draw)
    fill_side_draw_properties(node_props, "liquid", liquid_draw)

    comp_spec = params.get("comp_spec", {})
    comp_indexes = comp_spec.get("PEC_COMPS_index", [])
    if len(comp_indexes) >= 1:
        node_props["comp_spec_1_id"]["value"] = comp_indexes[0]
        node_props["comp_spec_1_id"]["realValue"] = comp_spec.get("PEC_COMPS", [None])[0]
        node_props["comp_spec_1_stage"]["value"] = comp_spec.get("SPEC_STREAMS", [None])[0]
        spec_1_phase = comp_spec.get("SPEC_PHASE", [None])[0]
        node_props["comp_spec_1_phase"]["realValue"] = "0" if spec_1_phase == "V" else "1"
        node_props["comp_spec_1_phase"]["value"] = "0" if spec_1_phase == "V" else "1"
        node_props["comp_spec_1_molar"]["value"] = comp_spec.get("SPEC_DESCRIP", [None])[0]

        if len(comp_indexes) >= 2:
            node_props["comp_spec_2_id"]["value"] = comp_indexes[1]
            node_props["comp_spec_2_id"]["realValue"] = comp_spec.get("PEC_COMPS", [None, None])[1]
            node_props["comp_spec_2_stage"]["value"] = comp_spec.get("SPEC_STREAMS", [None, None])[1]
            spec_2_phase = comp_spec.get("SPEC_PHASE", [None, None])[1]
            node_props["comp_spec_2_phase"]["realValue"] = "0" if spec_2_phase == "V" else "1"
            node_props["comp_spec_2_phase"]["value"] = "0" if spec_2_phase == "V" else "1"
            node_props["comp_spec_2_molar"]["value"] = comp_spec.get("SPEC_DESCRIP", [None, None])[1]
        else:
            node_props["comp_spec_2_id"] = {"isKeyword": True}
            node_props["comp_spec_2_stage"] = {"isKeyword": True}
            node_props["comp_spec_2_phase"] = {"isKeyword": True}
            node_props["top_product_molar_flowrate"] = {
                "isKeyword": True,
                "fixed": True,
                "unitType": "molar_flowrate",
                "value": params.get("top_molar_flowrate_guess", {}).get("value", 0),
                "unit": "mol/s",
            }

    condenser_type = params.get("CONDENSER", {}).get("value", "")
    if condenser_type == "PARTIAL-V-L":
        node_props["condenser_type"]["value"] = "1"
        node_props["condenser_type"]["realValue"] = "1"
        node_props["top_molar_vapor_fraction"]["value"] = params.get("top_vapor_fraction", {}).get("value")
        node_props["top_molar_vapor_fraction"]["fixed"] = True
    elif condenser_type == "TOTAL":
        node_props["condenser_type"]["value"] = "0"
        node_props["condenser_type"]["realValue"] = "0"
    elif condenser_type == "PARTIAL-V":
        node_props["condenser_type"]["value"] = "1"
        node_props["condenser_type"]["realValue"] = "1"
        node_props["top_molar_vapor_fraction"]["value"] = 1
        node_props["top_molar_vapor_fraction"]["fixed"] = True

    node_props["tray_1_pressure"]["value"] = params.get("tray_1_pressure", {}).get("value")
    node_props["tray_2_pressure"]["value"] = params.get("tray_2_pressure", {}).get("value")
    node_props["tray_pressure_drop"]["value"] = params.get("tray_pressure_drop", {}).get("value")
    node_props["tray_1_pressure"]["unit"] = params.get("tray_1_pressure", {}).get("unit", "")
    node_props["tray_2_pressure"]["unit"] = params.get("tray_2_pressure", {}).get("unit", "")
    node_props["tray_pressure_drop"]["unit"] = params.get("tray_pressure_drop", {}).get("unit", "")
    node_props["tray_pressure"]["value"] = params.get("tray_pressure", [])
    if "pressure_view" in params:
        pressure_view = params.get("pressure_view", {}).get("value")
        node_props["pressure_view"] = {
            "isKeyword": True,
            "fixed": True,
            "value": pressure_view,
            "realValue": pressure_view,
        }

    node_props["reflux_ratio_guess"]["value"] = params.get("reflux_ratio_guess", {}).get("value")
    node_props["top_molar_flowrate_guess"]["value"] = params.get("top_molar_flowrate_guess", {}).get("value")
    return node_props


def fill_side_draw_properties(node_props: NodeProps, phase: str, draw: Dict[str, Any]) -> None:
    """填充或清空精馏塔侧线参数。

    Column_properties.json 模板里可能带着历史示例侧线数据。当前 Aspen 塔没有
    侧线时必须显式清空，否则 ToP 会误以为每个塔都有侧线端口和侧线参数。
    """
    prefix = f"{phase}_side_draw"
    streams = draw.get("stream_name", [])
    stages = draw.get("stages", [])
    flows = draw.get("flow", [])

    if not streams:
        node_props[f"{prefix}_stages"] = {"isKeyword": True}
        node_props[f"{prefix}_flowrate_basis"] = {"isKeyword": True}
        node_props[f"{prefix}_molar_flowrate"] = {"isKeyword": True, "unitType": "molar_flowrate"}
        return

    row_headers = [f"{prefix}_{index}" for index in range(len(streams))]
    stages_prop = node_props[f"{prefix}_stages"]
    stages_prop["value"] = stages
    stages_prop["rowHeader"] = row_headers
    stages_prop["rows"] = streams
    stages_prop["rowSize"] = len(streams)

    flow_basis = node_props[f"{prefix}_flowrate_basis"]
    flow_basis["value"] = "0"
    flow_basis["realValue"] = "0"

    flow_prop = node_props[f"{prefix}_molar_flowrate"]
    flow_prop["value"] = flows
    flow_prop["unit"] = flow_prop.get("unit") or "mol/s"
    flow_prop["rowHeader"] = row_headers
    flow_prop["rows"] = streams
    flow_prop["rowSize"] = len(streams)


PROPERTY_FILLERS: Dict[str, PropertyFiller] = {
    # 新增设备时优先在这里注册填充函数，避免在 graph_builder 中堆 if-else。
    "Flash2": fill_flash,
    "Heater": fill_heater,
    "Pump": fill_pump,
    "Mixer": fill_mixer,
    "SSplit": fill_splitter,
    "FSplit": fill_splitter,
    "RadFrac": fill_column,
    "Sep": fill_component_splitter,
    "HeatX": fill_heatx,
    "Compr": fill_compressor,
    "Valve": fill_valve,
}
