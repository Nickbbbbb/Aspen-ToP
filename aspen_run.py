import os
import time
import json
import uuid
import win32com.client
import pythoncom
from typing import Dict, List, Any

from constants.ChemicalMapper import ChemicalMapper
from get_x_y import extract_coords_from_bkp


class AspenUnitExtractor:
    """Aspen 提取器：保留原有的物理数据提取逻辑，仅重构拓扑图生成"""

    def __init__(self, bkp_file_path: str):
        self.bkp_path = os.path.abspath(bkp_file_path)
        self.aspen = None
        self.tree = None
        self.components_list = []
        # 新增：用于缓存流股的连接关系 {stream_name: {"source": block_name, "dest": block_name}}
        self.stream_topology_map = {}

    def initialize(self) -> bool:
        if not os.path.exists(self.bkp_path):
            raise FileNotFoundError(f"文件未找到: {self.bkp_path}")
        print(f"🚀 正在启动 Aspen Plus...")
        try:
            pythoncom.CoInitialize()
            self.aspen = win32com.client.Dispatch("Apwn.Document")
            self.aspen.InitFromArchive2(self.bkp_path)
            self.aspen.Visible = True
            self.aspen.SuppressDialogs = 1
            self.tree = self.aspen.Tree

            # 加载组分
            comp_node = self.tree.FindNode(r"\Data\Components\Specifications\Input\OUTNAME")
            if comp_node:
                self.components_list = [c.Value for c in comp_node.Elements]

            return True
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            self.cleanup()
            raise

    def _get_val(self, path: str):
        try:
            node = self.tree.FindNode(path)
            return node.Value if node else None
        except:
            return None

    def _get_prop_with_unit(self, path: str, default_unit: str = "") -> Dict[str, Any]:
        try:
            node = self.tree.FindNode(path)
            if node:
                unit = getattr(node, "UnitString", default_unit)
                val = node.Value
                if val is None: val = 0.0
                return {"value": val, "unit": unit}
            else:
                return {"value": None, "unit": default_unit}
        except Exception:
            return {"value": None, "unit": default_unit}

    def _generate_uuid(self):
        return str(uuid.uuid4())

    # =========================================================================
    # PART 1: 物理数据提取 (完全保留你原来的逻辑，不做任何修改)
    # =========================================================================
    def get_physical_data(self) -> Dict[str, Any]:
        print("📊 [Part 1] 正在提取物理属性数据 (保持原样)...")
        data = {
            "components": {},
            "blocks": {},
            "streams": {},
            "params": {},
            "methad": ""
        }

        # 1. 组分
        components_fenzi = self.tree.FindNode(r"\Data\Components\Specifications\Input\ANAME")
        if components_fenzi:
            data["components"]["fenzi"] = [c.Value for c in components_fenzi.Elements]
            data["components"]["label"] = [c.Name for c in components_fenzi.Elements]
        components_cas = self.tree.FindNode(r"\Data\Components\Specifications\Input\CASN")
        if components_cas:
            data["components"]["cas"] = [c.Value for c in components_cas.Elements]
        components_name = self.tree.FindNode(r"\Data\Components\Specifications\Input\DBNAME")
        if components_name:
            data["components"]["aspen_name"] = [c.Value for c in components_name.Elements]
        top_name = []
        for aspen_name in data["components"]["aspen_name"]:
            local_name = ChemicalMapper.get_local_name_by_aspen(aspen_name)
            top_name.append(local_name)
        data["components"]["top_name"] = top_name


        # 2. 模块
        blocks_root = self.tree.FindNode(r"\Data\Blocks")
        if blocks_root:
            for block in blocks_root.Elements:
                b_name = block.Name
                # 提取连接信息
                inputs = []
                outputs = []
                ports = block.FindNode("Ports")

                # 在这里顺便建立拓扑缓存，因为inventory可能为空
                # 记录：流股X 进入了 Block Y
                # 记录：流股Z 离开了 Block Y
                block_type = block.AttributeValue(6)
                if ports:
                    in_n = ports.FindNode("F(IN)")
                    if in_n:
                        if block_type == "Mixer":
                            mixer_index = 0
                            for p in in_n.Elements:
                                s_name = p.Value
                                inputs.append({f"inlet_{mixer_index}": s_name})
                                mixer_index += 1
                                self._register_topology(s_name, dest=b_name)  # 记录拓扑
                        elif block_type == "RadFrac":
                            column_index = 0
                            for p in in_n.Elements:
                                s_name = p.Value
                                inputs.append({f"feed_in_{column_index}": s_name})
                                column_index += 1
                                self._register_topology(s_name, dest=b_name)  # 记录拓扑
                        else:
                            for p in in_n.Elements:
                                s_name = p.Value
                                inputs.append({"inlet_0": s_name})
                                self._register_topology(s_name, dest=b_name)  # 记录拓扑
                    # 精馏塔的上下出口
                    out_VD = ports.FindNode("VD(OUT)")
                    if out_VD:
                        for p in out_VD.Elements:
                            s_name = p.Value
                            outputs.append({"top_vapor_out_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    out_B = ports.FindNode("B(OUT)")
                    if out_B:
                        for p in out_B.Elements:
                            s_name = p.Value
                            outputs.append({"bottom_liquid_out_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    out_LD = ports.FindNode("LD(OUT)")
                    if out_LD:
                        for p in out_LD.Elements:
                            s_name = p.Value
                            outputs.append({"top_liquid_out_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    # 精馏塔侧线出口
                    if block_type == "RadFrac":
                        out_SP = ports.FindNode("SP(OUT)")
                        # 对应的流股名称  然后我们将其转为对应的塔板数
                        stream_name2VL = {}
                        for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\PROD_PHASE").Elements:
                            stream_name2VL[p.Name] = p.Value
                        if out_SP:
                            for p in out_SP.Elements:
                                s_name = p.Value
                                if stream_name2VL[s_name] == "L":
                                    outputs.append({"liquid_side_draw_0": s_name})
                                else:
                                    outputs.append({"vapor_side_draw_0": s_name})
                                self._register_topology(s_name, source=b_name)  # 记录拓扑

                    # Flash的气相
                    out_v = ports.FindNode("V(OUT)")
                    if out_v:
                        for p in out_v.Elements:
                            s_name = p.Value
                            outputs.append({"vapor_out_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    # Flash的液相
                    out_l = ports.FindNode("L(OUT)")
                    if out_l:
                        for p in out_l.Elements:
                            s_name = p.Value
                            outputs.append({"liquid_out_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑

                    out_p = ports.FindNode("P(OUT)")
                    if out_p:
                        if block_type == "SSplit" or block_type == "FSplit" or block_type == "Sep":
                            splitt_index = 0
                            for p in out_p.Elements:
                                s_name = p.Value
                                outputs.append({f"outlet_{splitt_index}": s_name})
                                splitt_index += 1
                                self._register_topology(s_name, source=b_name)  # 记录拓扑
                        else:
                            for p in out_p.Elements:
                                s_name = p.Value
                                outputs.append({"outlet_0": s_name})
                                self._register_topology(s_name, source=b_name)


                    # HeatX 换热器的四个进出口,单独处理
                    out_H = ports.FindNode("H(OUT)")
                    if out_H:
                        for p in out_H.Elements:
                            s_name = p.Value
                            outputs.append({"hot_stream_outlet_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    out_C = ports.FindNode("C(OUT)")
                    if out_C:
                        for p in out_C.Elements:
                            s_name = p.Value
                            outputs.append({"cold_stream_outlet_0": s_name})
                            self._register_topology(s_name, source=b_name)  # 记录拓扑
                    in_H = ports.FindNode("H(IN)")
                    if in_H:
                        for p in in_H.Elements:
                            s_name = p.Value
                            inputs.append({"hot_stream_inlet_0": s_name})
                            self._register_topology(s_name, dest=b_name)  # 记录拓扑
                    in_C = ports.FindNode("C(IN)")
                    if in_C:
                        for p in in_C.Elements:
                            s_name = p.Value
                            inputs.append({"cold_stream_inlet_0": s_name})
                            self._register_topology(s_name, dest=b_name)  # 记录拓扑
                params = self.get_block_data(b_name, block, data["components"].get("top_name", []), data["components"].get("label", []), outputs)
                data["blocks"][b_name] = {
                    "type": block.AttributeValue(6),
                    "in_streams": inputs,
                    "out_streams": outputs,
                    "params": params
                }

        # 3. 流股
        streams_root = self.tree.FindNode(r"\Data\Streams")
        inventory_root = self.tree.FindNode(r"\Data\Flowsheet\Inventory\Streams")
        if streams_root:
            for strm in streams_root.Elements:
                s_name = strm.Name
                base = fr"\Data\Streams\{s_name}\Input"

                # 拓扑 (保留原来的读取逻辑用于 connection 字段显示)
                inv_node = inventory_root.FindNode(s_name) if inventory_root else None
                source = inv_node.FindNode("Source").Value if inv_node and inv_node.FindNode("Source") else None
                dest = inv_node.FindNode("Destination").Value if inv_node and inv_node.FindNode("Destination") else None

                strm_data = {
                    "connection": {"from": source, "to": dest},
                    "properties": {
                        "temperature": self._get_prop_with_unit(fr"{base}\TEMP\MIXED"),
                        "pressure": self._get_prop_with_unit(fr"{base}\PRES\MIXED"),
                        "vapor_frac": self._get_prop_with_unit(fr"{base}\RES_VFRAC"),
                        "mass_flow": self._get_prop_with_unit(fr"{base}\MASSFLMX\MIXED"),
                        "mole_flow": self._get_prop_with_unit(fr"{base}\TOTFLOW\MIXED"),
                    },
                    "composition_mole_frac": {}
                }

                for comp_id in self.components_list:
                    val = self._get_val(fr"{base}\FLOW\MIXED\{comp_id}")
                    strm_data["composition_mole_frac"][comp_id] = val if val is not None else 0.0

                data["streams"][s_name] = strm_data

            methad_node = self.tree.FindNode(r"\Data\Properties\Specifications\Input\GBASEOPSET")
            if methad_node:
                data["methad"] = methad_node.Value
        return data

    def get_block_data(self, b_name, block, comp_name, comp_label, outputs) -> Dict[str, Any]:
        comp_len = len(comp_name)
        result = {}
        base = fr"\Data\Blocks\{b_name}\Input"
        # 简单判断是否包含FLASH字样
        blk_type = block.AttributeValue(6)
        if blk_type == "Flash2":
            # SPEC_OPT看闪蒸算法的选择
            result["SPEC_OPT"] = self._get_prop_with_unit(fr"{base}\SPEC_OPT")
            result["system_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["comp_nums"] = comp_len
            result["system_temperature"] = self._get_prop_with_unit(fr"{base}\TEMP")
            result["system_vapor_molar_fraction"] = self._get_prop_with_unit(fr"{base}\VFRAC")
            result["system_heat_duty"] = self._get_prop_with_unit(fr"{base}\DUTY")
        elif blk_type == "Heater":
            result["outlet_stream_temperature"] = self._get_prop_with_unit(fr"{base}\TEMP")
            result["comp_nums"] = comp_len
            result["outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
        elif blk_type == "Compr":
            result["outlet_stream_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["comp_nums"] = comp_len
            result["isentropic_efficiency"] = self._get_prop_with_unit(fr"{base}\SEFF")
            result["mechanical_efficiency"] = self._get_prop_with_unit(fr"{base}\MEFF")
        elif blk_type == "Pump":
            result["OPT_SPEC"] = self._get_prop_with_unit(fr"{base}\OPT_SPEC")
            result["outlet_stream_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["pressure_increase"] = self._get_prop_with_unit(fr"{base}\DELP")
            result["pressure_ratio"] = self._get_prop_with_unit(fr"{base}\PRATIO")
            result["total_power"] = self._get_prop_with_unit(fr"{base}\POWER")
            result["comp_nums"] = comp_len
            result["pumping_efficiency"] = self._get_prop_with_unit(fr"{base}\EFF")
        elif blk_type == "Valve":
            result["comp_nums"] = comp_len
            result["outlet_pressure"] = self._get_prop_with_unit(fr"{base}\P_OUT")
        elif blk_type == "Mixer":
            result["outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["comp_nums"] = comp_len
            result["no_inlets"] = 0
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\F(IN)").Elements:
                result["no_inlets"] += 1
        elif blk_type == "SSplit":
            result["outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["comp_nums"] = comp_len
            result["no_outlets"] = 0
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\P(OUT)").Elements:
                result["no_outlets"] += 1
            split_fraction_value = []
            split_fraction_rows = []
            split_fraction_rowHeader = []
            index = 0
            for out_streams in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRAC").Elements:
                value = self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRAC\{out_streams.Name}\MIXED").Value
                split_fraction_rows.append(out_streams.Name)
                split_fraction_value.append(value)
                split_fraction_rowHeader.append(f"outlet_{index}")
                index += 1
            result["split_fraction_value"] = split_fraction_value
            result["split_fraction_rows"] = split_fraction_rows
            result["split_fraction_rowHeader"] = split_fraction_rowHeader
        elif blk_type == "FSplit":
            result["outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES")
            result["comp_nums"] = comp_len
            result["no_outlets"] = 0
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\P(OUT)").Elements:
                result["no_outlets"] += 1
            split_fraction_value = []
            split_fraction_rows = []
            split_fraction_rowHeader = []
            index = 0
            current_FRAC = 0
            for out_streams in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRAC").Elements:
                stream_name = out_streams.Name
                FRAC_node = self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRAC\{out_streams.Name}")
                if FRAC_node.Value:
                    value = FRAC_node.Value
                    current_FRAC += value
                else:
                    value = 1 - current_FRAC
                split_fraction_rows.append(out_streams.Name)
                split_fraction_value.append(value)
                split_fraction_rowHeader.append(f"outlet_{index}")
                index += 1
            result["split_fraction_value"] = split_fraction_value
            result["split_fraction_rows"] = split_fraction_rows
            result["split_fraction_rowHeader"] = split_fraction_rowHeader
        elif blk_type == "HeatX":
            result["hot_outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES_HOT")
            result["cold_outlet_pressure"] = self._get_prop_with_unit(fr"{base}\PRES_COLD")
            result["comp_nums"] = comp_len
            result["area"] = self._get_prop_with_unit(fr"{base}\AREA")
            result["u_overall"] = self._get_prop_with_unit(fr"{base}\U")
        # 精馏塔:默认是分凝器,釜式
        elif blk_type == "RadFrac":
            # 首先确定出口流股的气态和液态 ####
            result["comp_nums"] = comp_len
            stream2Phas = {}
            """outputs = {
                    "top_vapor_out_0": "S5"
                },
                {
                    "bottom_liquid_out_0": "S6"
                }"""
            for port in outputs:
                key = list(port.keys())[0]
                value = list(port.values())[0]
                if key == "top_vapor_out_0" or key == "vapor_side_draw_0":
                    stream2Phas[value] = "V"
                elif key == "bottom_liquid_out_0" or key == "top_liquid_out_0" or key == "liquid_side_draw_0":
                    stream2Phas[value] = "L"
            # 冷凝器类型NONE  TOTAL   PARTIAL-V 这个就表示我们的分凝器+1    PARTIAL-V-L
            result["CONDENSER"] = self._get_prop_with_unit(fr"{base}\CONDENSER")
            # 塔板数
            result["no_trays"] = self._get_prop_with_unit(fr"{base}\NSTAGE")
            # 进料塔板 一个列表 要有值,有端口信息,有流股信息
            feed_trays_value = []
            feed_trays_rowHeader = []
            feed_trays_rows = []
            index = 0
            for out_streams in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FEED_STAGE").Elements:
                value = self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FEED_STAGE\{out_streams.Name}").Value
                feed_trays_rows.append(out_streams.Name)
                feed_trays_value.append(value)
                feed_trays_rowHeader.append(f"feed_in_{index}")
                index += 1
            result["feed_trays_value"] = feed_trays_value
            result["feed_trays_rows"] = feed_trays_rows
            result["feed_trays_rowHeader"] = feed_trays_rowHeader
            # 侧线塔板 一个列表 要有值,有端口信息,有流股信息
            side_trays_value = []
            side_trays_rowHeader = []
            side_trays_rows = []


            # 进料流股数
            result["no_feeds"] = 0
            in_nodes = self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\F(IN)")
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\F(IN)").Elements:
                result["no_feeds"] += 1
            # 读取液态和气态侧线的 名称 塔板数 相态 流量
            product_stream = {
                "stream_name": [],
                "PROD_FLOW": [],
                "PROD_PHASE": [],
                "PROD_STAGE": []
            }
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\PROD_FLOW").Elements:
                product_stream["stream_name"].append(p.Name)
                product_stream["PROD_FLOW"].append(p.Value)
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\PROD_PHASE").Elements:
                product_stream["PROD_PHASE"].append(p.Value)
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\PROD_STAGE").Elements:
                product_stream["PROD_STAGE"].append(p.Value)
            result["vapor_side_draw"] = {
                "stream_name":[],
                "stages": [],
                "flow": []
            }
            result["liquid_side_draw"] = {
                "stream_name":[],
                "stages": [],
                "flow": []
            }
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

            # 塔顶气化分率
            result["top_vapor_fraction"] = self._get_prop_with_unit(fr"{base}\BASIS_RDV")
            # 回流比
            result["top_molar_flowrate_guess"] = self._get_prop_with_unit(fr"{base}\BASIS_D")
            # 流出物流率(这里默认是质量流量)
            result["reflux_ratio_guess"] = self._get_prop_with_unit(fr"{base}\BASIS_RR")
            # 塔板 1/冷凝器压力  塔板 2 压力  塔板压降 再计算tray_pressure
            node = self.tree.FindNode(fr"{base}\DP_STAGE")
            result["tray_1_pressure"] = self._get_prop_with_unit(fr"{base}\PRES1")
            result["tray_2_pressure"] = self._get_prop_with_unit(fr"{base}\PRES2")
            result["tray_pressure_drop"] = self._get_prop_with_unit(fr"{base}\DP_STAGE")
            if result["tray_2_pressure"]["value"] == 0:
                result["tray_2_pressure"] = result["tray_1_pressure"]
                result["tray_pressure_drop"] = {"value": 0, "unit": "Pa"}
            if node:
                val = node.Value
                if val is None:
                    index = 1
                    for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\STAGE_PRES").Elements:
                        if index == 1:
                            result["tray_1_pressure"] = {"value": p.Value, "unit": "Pa"}
                            index += 1
                        elif index == 2:
                            result["tray_2_pressure"] = {"value": p.Value, "unit": "Pa"}
                            index += 1
                        else:
                            result["tray_pressure_drop"] = {"value": (p.Value - result["tray_2_pressure"]["value"])/(int(p.Name) - 2), "unit": "Pa"}
                        product_stream["stream_name"].append(p.Name)
                        product_stream["PROD_FLOW"].append(p.Value)

            result["tray_pressure"] = self.calculate_tray_pressures(result["no_trays"]["value"], result["tray_1_pressure"]["value"],
                                                               result["tray_2_pressure"]["value"], result["tray_pressure_drop"]["value"])

            # 判断是否有设计规范，如果有那么我们top的两个设计规定都是这个组分分率设置
            result["comp_spec"] = {
                "SPEC_TYPE": [],
                "SPEC_PHASE": [],
                "PEC_COMPS": [],
                "PEC_COMPS_index": [],
                "SPEC_STREAMS": [],
                "SPEC_DESCRIP": []
            }
            SPEC_TYPE = []
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\SPEC_TYPE").Elements:
                SPEC_TYPE.append(p.Value)
            if len(SPEC_TYPE):
                SPEC_PHASE = []
                PEC_COMPS = []
                PEC_COMPS_index = []
                for i in range(len(SPEC_TYPE)):
                    path = fr"\Data\Blocks\{b_name}\Input\SPEC_COMPS\{i+1}\#0"
                    label_name = self.tree.FindNode(path).Value
                    for i in range(len(comp_label)):
                        if comp_label[i] == label_name:
                            PEC_COMPS.append(comp_name[i])
                            PEC_COMPS_index.append(i)
                            break
                # 对应的流股名称  然后我们将其转为对应的塔板数  / 通过stream的名字通过看他在哪个端口，来选择他的相态
                SPEC_STREAMS = []
                for i in range(len(SPEC_TYPE)):
                    path = fr"\Data\Blocks\{b_name}\Input\SPEC_STREAMS\{i+1}\#0"
                    stream_name = self.tree.FindNode(path).Value
                    SPEC_PHASE.append(stream2Phas[stream_name])
                    for i in range(len(product_stream["stream_name"])):
                        if stream_name == product_stream["stream_name"][i]:
                            SPEC_STREAMS.append(product_stream["PROD_STAGE"][i])
                            break
                SPEC_DESCRIP = []
                for i in range(len(SPEC_TYPE)):
                    path = fr"\Data\Blocks\{b_name}\Input\SPEC_DESCRIP\{i + 1}"
                    value = float(self.tree.FindNode(path).Value.split(',')[1].strip())
                    SPEC_DESCRIP.append(value)
                # 将组分分率规定保存
                result["comp_spec"] = {
                    "SPEC_TYPE": SPEC_TYPE,
                    "SPEC_PHASE": SPEC_PHASE,
                    "PEC_COMPS": PEC_COMPS,
                    "PEC_COMPS_index": PEC_COMPS_index,
                    "SPEC_STREAMS": SPEC_STREAMS,
                    "SPEC_DESCRIP": SPEC_DESCRIP
                }

            # 侧线：给侧线添加塔板数，流量

        elif blk_type == "RStoic":




        # 组分分离器
        elif blk_type == "Sep":
            result["comp_nums"] = comp_len
            result["no_outlets"] = 0
            for p in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Ports\P(OUT)").Elements:
                result["no_outlets"] += 1
            # 分离值 [ 1, 1, 0, 0, 0, 0 ]
            split_fractions_value = []
            # 流股名字 [ "s-2", "s-3" ]
            split_fractions_rows = []
            # port名字 [ "outlet_0", "outlet_1" ]
            split_fractions_rowHeader = []
            # 两个都是物质名字 [ "METHANE", "ETHYLENE", "PROPANE" ]
            split_fractions_cols = comp_name
            split_fractions_colHeader = comp_name
            index = 0
            for out_stream in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRACS").Elements:
                split_fractions_rowHeader.append(f"outlet_{index}")
                split_fractions_rows.append(out_stream.Name)
                index += 1
                for comp in self.tree.FindNode(fr"\Data\Blocks\{b_name}\Input\FRACS\{out_stream.Name}\MIXED").Elements:
                    if comp.Value:
                        split_fractions_value.append(comp.Value)
                    else:
                        split_fractions_value.append(0)
            result["split_fractions_value"] = split_fractions_value
            result["split_fractions_rows"] = split_fractions_rows
            result["split_fractions_rowHeader"] = split_fractions_rowHeader
            result["split_fractions_cols"] = split_fractions_cols
            result["split_fractions_colHeader"] = split_fractions_colHeader


        return result

    def calculate_tray_pressures(self, no_trays, tray_1_p, tray_2_p, p_drop):
        """
        根据给定的参数计算精馏塔各级压力分布列表。

        :param no_trays: 总塔板数 (Int), 例如 40
        :param tray_1_p: 第1级(冷凝器)压力 (Float/Int), 例如 90000
        :param tray_2_p: 第2级(塔顶板)压力 (Float/Int), 例如 95000
        :param p_drop: 塔板压降 (Float/Int), 例如 125
        :return: 包含每一级压力的列表
        """
        if no_trays <= 0:
            return []

        # 初始化列表
        pressures = []

        # 第1级：直接使用 tray_1_pressure
        pressures.append(tray_1_p)

        if no_trays >= 2:
            # 第2级：直接使用 tray_2_pressure
            pressures.append(tray_2_p)

            # 第3级及以后：在前一级基础上累加压降
            # 循环范围是从第3级(索引2)开始，直到第 no_trays 级
            for i in range(2, no_trays):
                prev_pressure = pressures[-1]
                new_pressure = prev_pressure + p_drop
                pressures.append(new_pressure)

        return pressures

    # 辅助方法：在遍历Block时构建可靠的拓扑关系
    def _register_topology(self, stream_name, source=None, dest=None):
        if stream_name not in self.stream_topology_map:
            self.stream_topology_map[stream_name] = {"source": None, "dest": None}
        if source:
            self.stream_topology_map[stream_name]["source"] = source
        if dest:
            self.stream_topology_map[stream_name]["dest"] = dest

    # =========================================================================
    # PART 2: 仅修改 processGraph 生成部分
    # =========================================================================
    def get_process_graph(self) -> Dict[str, Any]:
        print("🕸️ [Part 2] 正在构建 Process Graph (基于Block端口扫描)...")

        nodes = []
        edges = []
        node_lookup = {}  # id -> node

        # 1. 添加 Blocks (必定是节点)
        blocks_root = self.tree.FindNode(r"\Data\Blocks")
        if blocks_root:
            for block in blocks_root.Elements:
                blk_name = block.Name
                # 获取模块类型
                blk_type = block.AttributeValue(6)

                node = {
                    "id": blk_name,
                    "type": blk_type,
                    "data": {"label": blk_name, "aspentype": blk_type},
                    "x": 0, "y": 0,
                    "_inputs": []  # 临时字段，用于排序
                }
                nodes.append(node)
                node_lookup[blk_name] = node

        # 2. 分析流股，决定是"边"还是"节点"
        # 使用 self.stream_topology_map，这比 inventory 更可靠
        streams_root = self.tree.FindNode(r"\Data\Streams")
        if streams_root:
            for strm in streams_root.Elements:
                s_name = strm.Name

                # 从缓存中获取连接信息
                topo = self.stream_topology_map.get(s_name, {"source": None, "dest": None})
                src_blk = topo["source"]
                dst_blk = topo["dest"]

                start_node_id = None
                end_node_id = None

                # --- 确定起点 ---
                if src_blk and src_blk in node_lookup:
                    # 起点是 Block -> 流股只是线
                    start_node_id = src_blk
                else:
                    # 起点无 -> 进料 Source 节点
                    start_node_id = s_name
                    if start_node_id not in node_lookup:
                        node = {
                            "id": start_node_id,
                            "type": "Source",
                            "data": {"label": s_name},
                            "x": 0, "y": 0,
                            "_inputs": []
                        }
                        nodes.append(node)
                        node_lookup[start_node_id] = node

                # --- 确定终点 ---
                if dst_blk and dst_blk in node_lookup:
                    # 终点是 Block -> 流股只是线
                    end_node_id = dst_blk
                else:
                    # 终点无 -> 产品 Sink 节点
                    end_node_id = s_name
                    if end_node_id not in node_lookup:
                        node = {
                            "id": end_node_id,
                            "type": "Sink",
                            "data": {"label": s_name},
                            "x": 0, "y": 0,
                            "_inputs": []
                        }
                        nodes.append(node)
                        node_lookup[end_node_id] = node

                # --- 创建 Edge ---
                if start_node_id and end_node_id:
                    edges.append({
                        "source": start_node_id,
                        "target": end_node_id,
                        "label": s_name
                    })
                    # 记录依赖关系，给后面的排序算法用
                    if end_node_id in node_lookup:
                        node_lookup[end_node_id]["_inputs"].append(start_node_id)

        # 3. 自动坐标计算 (Ranked Layout)
        self._calculate_coordinates(nodes)

        # 清理临时字段
        final_nodes = []
        for n in nodes:
            n_clean = {k: v for k, v in n.items() if k != "_inputs"}
            final_nodes.append(n_clean)

        return {
            "processGraph": {  # 修改为 processGraph
                "id": self._generate_uuid(),
                "createBy": "AspenExtractor",
                "updateTime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "nodes": final_nodes,
                "edges": edges
            }
        }

    def _calculate_coordinates(self, nodes):
        """简单的自动布局"""
        node_map = {n["id"]: n for n in nodes}

        # 初始化 Rank
        for n in nodes:
            # 返回结果 {"id": target_id, "x": float(x), "y": float(y)}
            graph_infp = extract_coords_from_bkp(self.bkp_path, n["id"])
            n["x"] = graph_infp["x"] * 100
            n["y"] = graph_infp["y"] * -100

    def cleanup(self):
        if self.aspen:
            try:
                self.aspen.Close()
                self.aspen.Quit()
            except:
                pass
        pythoncom.CoUninitialize()


# =========================================================================
# 执行入口
# =========================================================================
def run_and_export(bkp_path, output_json):
    extractor = AspenUnitExtractor(bkp_path)
    try:
        if extractor.initialize():
            phys_data = extractor.get_physical_data()
            graph_data = extractor.get_process_graph()
            # 合并数据
            final_result = {**phys_data, **graph_data}

            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(final_result, f, indent=4, ensure_ascii=False)
            print(f"✨ 导出完成！")
            print(f"文件位置: {output_json}")
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    BKP = r"C:\Users\Administrator\Downloads\export-test\aspen_result\乙烯塔\乙烯塔.bkp"
    OUT = "aspen_fixed_data.json"

    run_and_export(BKP, OUT)