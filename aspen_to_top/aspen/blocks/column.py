from typing import Dict, Any, List
from .base import BaseBlockExtractor
from ...utils.chemical_mapper import ChemicalMapper


class ColumnExtractor(BaseBlockExtractor):
    """RadFrac 精馏塔提取器。

    精馏塔参数在 Aspen Tree 中分散得比较多，这里统一整理成较平的 params：
    塔板数、进料板、冷凝器类型、压力分布、侧线采出和初值等。
    """

    @staticmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        base = fr"\Data\Blocks\{block_name}\Input"

        # 根据端口解析结果预先记录产品流股相态，后续侧线采出会用到。
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
        # FEED_STAGE 子节点名通常就是进料流股名，Value 是对应进料塔板。
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
        in_nodes = tree.FindNode(fr"\Data\Blocks\{block_name}\Ports\F(IN)")
        if not in_nodes:
            in_nodes = tree.FindNode(fr"{block_name}\Ports\F(IN)")
        if in_nodes:
            no_feeds = len(list(in_nodes.Elements))
        elif feed_trays_rows:
            no_feeds = len(feed_trays_rows)
        result["no_feeds"] = no_feeds

        product_stream = {"stream_name": [], "PROD_FLOW": [], "PROD_PHASE": [], "PROD_STAGE": []}
        # 侧线产品由 PROD_FLOW / PROD_PHASE / PROD_STAGE 三组表共同描述。
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
        result["pressure_view"] = ColumnExtractor.get_prop(tree, fr"{base}\VIEW_PRES")

        if result["tray_2_pressure"]["value"] == 0:
            # Aspen 有时只给第一块板压力；这里补齐 ToP 需要的第二块板压力和压降。
            result["tray_2_pressure"] = result["tray_1_pressure"]
            result["tray_pressure_drop"] = {"value": 0, "unit": "Pa"}

        dp_node = tree.FindNode(fr"{base}\DP_STAGE")
        if dp_node:
            val = dp_node.Value
            if val is None:
                # 如果没有统一压降，则尝试读取 STAGE_PRES 表中的前两块板压力。
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
                        else:
                            # Aspen 没有直接给 DP_STAGE 时，原逻辑用第三个及后续
                            # STAGE_PRES 节点反推平均每板压降。
                            result["tray_pressure_drop"] = {
                                "value": (p.Value - result["tray_2_pressure"]["value"]) / (int(p.Name) - 2),
                                "unit": "Pa",
                            }

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

        comp_labels = []
        comp_names = []
        comp_label_node = tree.FindNode(r"\Data\Components\Specifications\Input\ANAME")
        comp_name_node = tree.FindNode(r"\Data\Components\Specifications\Input\DBNAME")
        if comp_label_node:
            comp_labels = [item.Name for item in comp_label_node.Elements]
        if comp_name_node:
            comp_names = [
                ChemicalMapper.get_local_name_by_aspen(item.Value)
                for item in comp_name_node.Elements
            ]

        spec_type_node = tree.FindNode(fr"{base}\SPEC_TYPE")
        spec_types = [item.Value for item in spec_type_node.Elements] if spec_type_node else []
        if spec_types:
            spec_phases = []
            spec_comps = []
            spec_comp_indexes = []
            spec_streams = []
            spec_descrip = []

            for index in range(len(spec_types)):
                comp_node = tree.FindNode(fr"{base}\SPEC_COMPS\{index + 1}\#0")
                label_name = comp_node.Value if comp_node else None
                if label_name in comp_labels:
                    comp_index = comp_labels.index(label_name)
                    spec_comp_indexes.append(comp_index)
                    spec_comps.append(comp_names[comp_index] if comp_index < len(comp_names) else label_name)

            for index in range(len(spec_types)):
                stream_node = tree.FindNode(fr"{base}\SPEC_STREAMS\{index + 1}\#0")
                stream_name = stream_node.Value if stream_node else None
                if not stream_name:
                    continue

                spec_phases.append(stream2Phas.get(stream_name))

                if stream_name in product_stream["stream_name"]:
                    stream_index = product_stream["stream_name"].index(stream_name)
                    spec_streams.append(product_stream["PROD_STAGE"][stream_index])
                elif stream_name == next(iter(stream2Phas.keys()), None):
                    spec_streams.append(1)
                elif stream_name in stream2Phas:
                    if stream2Phas[stream_name] == "V":
                        spec_streams.append(1)
                    else:
                        spec_streams.append(result["no_trays"]["value"])

            for index in range(len(spec_types)):
                desc_node = tree.FindNode(fr"{base}\SPEC_DESCRIP\{index + 1}")
                if desc_node and desc_node.Value:
                    spec_descrip.append(float(str(desc_node.Value).split(",")[1].strip()))

            result["comp_spec"] = {
                "SPEC_TYPE": spec_types,
                "SPEC_PHASE": spec_phases,
                "PEC_COMPS": spec_comps,
                "PEC_COMPS_index": spec_comp_indexes,
                "SPEC_STREAMS": spec_streams,
                "SPEC_DESCRIP": spec_descrip,
            }

        return result

    @staticmethod
    def calculate_tray_pressures(no_trays, tray_1_p, tray_2_p, p_drop):
        """根据塔板数、前两块板压力和每板压降推算整塔压力表。"""
        if no_trays <= 0:
            return []

        pressures = []
        pressures.append(tray_1_p)

        if no_trays >= 2:
            pressures.append(tray_2_p)
            for i in range(2, no_trays):
                pressures.append(pressures[-1] + p_drop)

        return pressures
