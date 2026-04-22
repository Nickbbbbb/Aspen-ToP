from typing import Dict, Any, List
from .base import BaseBlockExtractor


class ColumnExtractor(BaseBlockExtractor):
    """RadFrac 精馏塔提取器"""

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"

        stream2Phas = {}
        for port in outputs:
            key = list(port.keys())[0]
            value = list(port.values())[0]
            if key == "top_vapor_out_0" or key == "vapor_side_draw_0":
                stream2Phas[value] = "V"
            elif key in ("bottom_liquid_out_0", "top_liquid_out_0", "liquid_side_draw_0"):
                stream2Phas[value] = "L"

        result = {
            "comp_nums": comp_count,
            "CONDENSER": ColumnExtractor.get_prop(tree, fr"{base}\CONDENSER"),
            "no_trays": ColumnExtractor.get_prop(tree, fr"{base}\NSTAGE"),
        }

        feed_trays_value = []
        feed_trays_rows = []
        feed_trays_rowHeader = []
        index = 0
        feed_stage_node = tree.FindNode(fr"{base}\FEED_STAGE")
        if feed_stage_node:
            for out_streams in feed_stage_node.Elements:
                value = tree.FindNode(fr"{base}\FEED_STAGE\{out_streams.Name}").Value
                feed_trays_rows.append(out_streams.Name)
                feed_trays_value.append(value)
                feed_trays_rowHeader.append(f"feed_in_{index}")
                index += 1
        result["feed_trays_value"] = feed_trays_value
        result["feed_trays_rows"] = feed_trays_rows
        result["feed_trays_rowHeader"] = feed_trays_rowHeader

        no_feeds = 0
        in_nodes = tree.FindNode(fr"{block_name}\Ports\F(IN)")
        if in_nodes:
            no_feeds = len(list(in_nodes.Elements))
        result["no_feeds"] = no_feeds

        product_stream = {"stream_name": [], "PROD_FLOW": [], "PROD_PHASE": [], "PROD_STAGE": []}
        prod_flow_node = tree.FindNode(fr"{base}\PROD_FLOW")
        if prod_flow_node:
            for p in prod_flow_node.Elements:
                product_stream["stream_name"].append(p.Name)
                product_stream["PROD_FLOW"].append(p.Value)

        prod_phase_node = tree.FindNode(fr"{base}\PROD_PHASE")
        if prod_phase_node:
            for p in prod_phase_node.Elements:
                product_stream["PROD_PHASE"].append(p.Value)

        prod_stage_node = tree.FindNode(fr"{base}\PROD_STAGE")
        if prod_stage_node:
            for p in prod_stage_node.Elements:
                product_stream["PROD_STAGE"].append(p.Value)

        result["vapor_side_draw"] = {"stream_name": [], "stages": [], "flow": []}
        result["liquid_side_draw"] = {"stream_name": [], "stages": [], "flow": []}

        for index, value in enumerate(product_stream["PROD_FLOW"]):
            if value:
                if product_stream["PROD_PHASE"][index] == "V":
                    result["vapor_side_draw"]["stream_name"].append(product_stream["stream_name"][index])
                    result["vapor_side_draw"]["stages"].append(product_stream["PROD_STAGE"][index])
                    result["vapor_side_draw"]["flow"].append(product_stream["PROD_FLOW"][index])
                else:
                    result["liquid_side_draw"]["stream_name"].append(product_stream["stream_name"][index])
                    result["liquid_side_draw"]["stages"].append(product_stream["PROD_STAGE"][index])
                    result["liquid_side_draw"]["flow"].append(product_stream["PROD_FLOW"][index])

        result["top_vapor_fraction"] = ColumnExtractor.get_prop(tree, fr"{base}\BASIS_RDV")
        result["top_molar_flowrate_guess"] = ColumnExtractor.get_prop(tree, fr"{base}\BASIS_D")
        result["reflux_ratio_guess"] = ColumnExtractor.get_prop(tree, fr"{base}\BASIS_RR")

        result["tray_1_pressure"] = ColumnExtractor.get_prop(tree, fr"{base}\PRES1")
        result["tray_2_pressure"] = ColumnExtractor.get_prop(tree, fr"{base}\PRES2")
        result["tray_pressure_drop"] = ColumnExtractor.get_prop(tree, fr"{base}\DP_STAGE")

        if result["tray_2_pressure"]["value"] == 0:
            result["tray_2_pressure"] = result["tray_1_pressure"]
            result["tray_pressure_drop"] = {"value": 0, "unit": "Pa"}

        dp_node = tree.FindNode(fr"{base}\DP_STAGE")
        if dp_node:
            val = dp_node.Value
            if val is None:
                index = 1
                stage_pres_node = tree.FindNode(fr"{base}\STAGE_PRES")
                if stage_pres_node:
                    for p in stage_pres_node.Elements:
                        if index == 1:
                            result["tray_1_pressure"] = {"value": p.Value, "unit": "Pa"}
                            index += 1
                        elif index == 2:
                            result["tray_2_pressure"] = {"value": p.Value, "unit": "Pa"}
                            index += 1

        result["tray_pressure"] = ColumnExtractor.calculate_tray_pressures(
            result["no_trays"]["value"],
            result["tray_1_pressure"]["value"],
            result["tray_2_pressure"]["value"],
            result["tray_pressure_drop"]["value"]
        )

        result["comp_spec"] = {
            "SPEC_TYPE": [],
            "SPEC_PHASE": [],
            "PEC_COMPS": [],
            "PEC_COMPS_index": [],
            "SPEC_STREAMS": [],
            "SPEC_DESCRIP": []
        }

        return result

    @staticmethod
    def calculate_tray_pressures(no_trays, tray_1_p, tray_2_p, p_drop):
        if no_trays <= 0:
            return []

        pressures = []
        pressures.append(tray_1_p)

        if no_trays >= 2:
            pressures.append(tray_2_p)
            for i in range(2, no_trays):
                pressures.append(pressures[-1] + p_drop)

        return pressures
