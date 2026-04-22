from typing import Any, Callable, Dict


NodeProps = Dict[str, Any]
BlockInfo = Dict[str, Any]
PropertyFiller = Callable[[NodeProps, Dict[str, Any]], NodeProps]


def fill_block_properties(block_name: str, block_info: BlockInfo, node_props: NodeProps) -> NodeProps:
    """Fill ToP node properties for one Aspen block."""
    params = block_info.get("params", {})
    block_type = block_info["type"]
    filler = PROPERTY_FILLERS.get(block_type)
    if not filler:
        return node_props
    return filler(node_props, params)


def fill_flash(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
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
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["outlet_stream_temperature"]["value"] = params.get("outlet_stream_temperature", {}).get("value")
    node_props["outlet_stream_temperature"]["unit"] = params.get("outlet_stream_temperature", {}).get("unit", "")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_pump(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
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
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["no_inlets"]["value"] = params.get("no_inlets", 0)
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_splitter(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    node_props["outlet_pressure"]["unit"] = params.get("outlet_pressure", {}).get("unit", "")
    node_props["no_outlets"]["value"] = params.get("no_outlets", 0)
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["split_fraction"]["value"] = params.get("split_fraction_value", [])
    node_props["split_fraction"]["rowHeader"] = params.get("split_fraction_rowHeader", [])
    return node_props


def fill_component_splitter(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["no_outlets"]["value"] = params.get("no_outlets", 0)
    node_props["split_fractions"]["value"] = params.get("split_fractions_value", [])
    node_props["split_fractions"]["rowHeader"] = params.get("split_fractions_rowHeader", [])
    node_props["split_fractions"]["colHeader"] = params.get("split_fractions_colHeader", [])
    node_props["split_fractions"]["cols"] = params.get("split_fractions_cols", [])
    return node_props


def fill_heatx(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
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
    node_props["outlet_stream_pressure"]["value"] = params.get("outlet_stream_pressure", {}).get("value")
    node_props["outlet_stream_pressure"]["unit"] = params.get("outlet_stream_pressure", {}).get("unit", "")
    node_props["isentropic_efficiency"]["value"] = params.get("isentropic_efficiency", {}).get("value")
    node_props["mechanical_efficiency"]["value"] = params.get("mechanical_efficiency", {}).get("value")
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props


def fill_valve(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    node_props["outlet_pressure"]["value"] = params.get("outlet_pressure", {}).get("value")
    return node_props


def fill_column(node_props: NodeProps, params: Dict[str, Any]) -> NodeProps:
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

    node_props["reflux_ratio_guess"]["value"] = params.get("reflux_ratio_guess", {}).get("value")
    node_props["top_molar_flowrate_guess"]["value"] = params.get("top_molar_flowrate_guess", {}).get("value")
    return node_props


PROPERTY_FILLERS: Dict[str, PropertyFiller] = {
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
