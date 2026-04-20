import json
import uuid
import copy
import random
import string
import secrets

from constants.ChemicalMapper import ChemicalMapper
from layout_fixed import fix_canvas_layout


# 生成projectId
def generate_projectId(length=8):
    """生成指定位数的十六进制随机ID"""
    # 每个十六进制字符是4位，所以总位数是 length * 4
    random_bytes = secrets.randbits(length * 4)
    # 格式化为十六进制，去掉前面的0x，确保小写
    projectId = format(random_bytes, f'0{length}x')
    return projectId


###########################################
#######  omProcessArchive
###########################################
def create_omProcessArchive(projectId, processId):
    omProcessArchive = {
        "createTime": "2026-02-04 06:37:43",
        "currentFlag": 1,
        "id": "2018936993196044289",
        "processId": "0f44e560",
        "projectId": "85b7aaee",
        "runStatus": 0,
        "syncGraphVersion": 23,
        "syncParamVersion": 22,
        "updateTime": "2026-02-04 06:37:43",
        "uuid": "d5c2c26a",
        "versionNo": "latest"
    }
    omProcessArchive["processId"] = processId
    omProcessArchive["projectId"] = projectId
    return omProcessArchive


###########################################
#######  omProject
###########################################
def create_omProject(projectId):
    omProject = {
        "coverPath": "",
        "createBy": "admin",
        "delFlag": "0",
        "groupId": "44c467d8",
        "id": "25be3df3",
        "orderNo": 0,
        "projectName": "flash_test",
        "publicFlag": "0",
        "unitSetId": "default",
        "updateTime": "2026-02-03 02:13:54"
    }
    omProject["id"] = projectId
    omProject["projectName"] = "nick11"
    return omProject


###########################################
#######  omProcessGraph
###########################################
def create_omProcessGraph(input_data, map_of_id, projectId, processId):
    omProcessGraph = {
        "createBy": "admin",
        "createTime": "2026-01-30 06:12:16",
        "delFlag": "0",
        "graphType": 1,
        "id": "2703da52",
        "processEdges": "",
        "processNodes": "",
        "projectId": "13300115",
        "updateBy": "admin",
        "updateTime": "2026-01-30 06:12:16"
    }
    omProcessGraph["processEdges"] = json.dumps(create_omProcessGraph_processEdges(input_data, map_of_id),
                                                ensure_ascii=False)
    omProcessGraph["processNodes"] = json.dumps(create_omProcessGraph_processNodes(input_data, map_of_id, create_omProcessGraph_processEdges(input_data, map_of_id)),
                                                ensure_ascii=False)
    omProcessGraph["id"] = processId
    omProcessGraph["projectId"] = projectId
    return omProcessGraph


def create_omProcessGraph_processEdges(input_data, map_of_id):
    processEdges_result = []
    connect_info = extract_connections(input_data["blocks"])
    with open("Template/processEdges_connetion.json", 'r', encoding='utf-8') as f:
        node_template = json.load(f)
    current_index = 1
    for connect in connect_info:
        # 深拷贝模板
        node_params = copy.deepcopy(node_template)

        uid = str(uuid.uuid4())
        # 第一种格式: uuid_s-下标
        connect_id = f"{uid}_s-{current_index}"
        # 第二种格式: s_下标
        connect_label = f"s_{current_index}"
        current_index += 1
        # node_params["attrs"]["label"] = connect_label
        node_params["attrs"]["label"] = connect["connect"]
        node_params["id"] = connect_id
        node_params["source"]["cell"] = map_of_id[connect["from"]]
        node_params["source"]["port"] = connect["from_port"]
        node_params["target"]["cell"] = map_of_id[connect["to"]]
        node_params["target"]["port"] = connect["to_port"]
        processEdges_result.append(node_params)

    return processEdges_result


# map_of_id是生成的我们对应的id 如:"FLASH1" : "54a52706_000cb682_FLASH1"
def create_omProcessGraph_processNodes(input_data, map_of_id, connect_info):
    result = []
    # 设置各个设备的参数 如温度,压力 还有ID,x,y坐标等
    for id, block in input_data["blocks"].items():
        if block["type"] == "Flash2":
            with open("Template/nodeProperties/Flash_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["system_pressure"]["value"] = block["params"]["system_pressure"]["value"]
            node_params["system_pressure"]["unit"] = block["params"]["system_pressure"]["unit"]
            spec_opt = block["params"]["SPEC_OPT"]["value"]
            if spec_opt == "TP":
                node_params["system_temperature"]["value"] = block["params"]["system_temperature"]["value"]
                node_params["system_temperature"]["unit"] = block["params"]["system_temperature"]["unit"]
                node_params["system_temperature"]["fixed"] = True
                node_params["Thermal_specification"]["value"] = "0"
                node_params["Thermal_specification"]["realValue"] = "0"
            elif spec_opt == "PV":
                node_params["system_vapor_molar_fraction"]["value"] = block["params"]["system_vapor_molar_fraction"]["value"]
                node_params["system_vapor_molar_fraction"]["unit"] = "mol/mol"
                node_params["system_temperature"]["fixed"] = True
                node_params["Thermal_specification"]["value"] = "1"
                node_params["Thermal_specification"]["realValue"] = "1"
            elif spec_opt == "PD":
                node_params["system_heat_duty"]["value"] = block["params"]["system_heat_duty"]["value"]
                node_params["system_heat_duty"]["unit"] = "J/s"
                node_params["system_temperature"]["fixed"] = True
                node_params["Thermal_specification"]["value"] = "2"
                node_params["Thermal_specification"]["realValue"] = "2"
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]

            with open("Template/processNodes/processNodes_Flash.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Heater":
            with open("Template/nodeProperties/Heater_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["outlet_pressure"]["value"] = block["params"]["outlet_pressure"]["value"]
            node_params["outlet_pressure"]["unit"] = block["params"]["outlet_pressure"]["unit"]
            node_params["outlet_stream_temperature"]["value"] = block["params"]["outlet_stream_temperature"]["value"]
            node_params["outlet_stream_temperature"]["unit"] = block["params"]["outlet_stream_temperature"]["unit"]
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            with open("Template/processNodes/processNodes_Heater.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Compr":
            with open("Template/nodeProperties/Compressor_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["outlet_stream_pressure"]["value"] = block["params"]["outlet_stream_pressure"]["value"]
            node_params["outlet_stream_pressure"]["unit"] = block["params"]["outlet_stream_pressure"]["unit"]
            node_params["isentropic_efficiency"]["value"] = block["params"]["isentropic_efficiency"]["value"]
            node_params["mechanical_efficiency"]["value"] = block["params"]["mechanical_efficiency"]["value"]
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            with open("Template/processNodes/processNodes_Compressor.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Pump":
            with open("Template/nodeProperties/Pump_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            OPT_SPEC = block["params"]["OPT_SPEC"]["value"]
            if OPT_SPEC == "PRES":
                node_params["outlet_specification"]["value"] = "0"
                node_params["outlet_specification"]["realValue"] = "0"
                node_params["outlet_stream_pressure"]["value"] = block["params"]["outlet_stream_pressure"]["value"]
                node_params["outlet_stream_pressure"]["unit"] = block["params"]["outlet_stream_pressure"]["unit"]
                node_params["outlet_stream_pressure"]["fixed"] = True
            elif OPT_SPEC == "DELP":
                node_params["outlet_specification"]["value"] = "1"
                node_params["outlet_specification"]["realValue"] = "1"
                node_params["pressure_increase"]["value"] = block["params"]["pressure_increase"]["value"]
                node_params["pressure_increase"]["unit"] = block["params"]["pressure_increase"]["unit"]
                node_params["outlet_stream_pressure"]["fixed"] = True
            elif OPT_SPEC == "PRATIO":
                node_params["outlet_specification"]["value"] = "2"
                node_params["outlet_specification"]["realValue"] = "2"
                node_params["pressure_ratio"]["value"] = block["params"]["pressure_ratio"]["value"]
                node_params["pressure_ratio"]["unit"] = "-"
                node_params["outlet_stream_pressure"]["fixed"] = True
            elif OPT_SPEC == "POWER":
                node_params["outlet_specification"]["value"] = "3"
                node_params["outlet_specification"]["realValue"] = "3"
                node_params["total_power"]["value"] = block["params"]["total_power"]["value"]
                node_params["total_power"]["unit"] = block["params"]["total_power"]["unit"]
                node_params["outlet_stream_pressure"]["fixed"] = True
            node_params["pumping_efficiency"]["value"] = block["params"]["pumping_efficiency"]["value"]
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            with open("Template/processNodes/processNodes_Pump.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Valve":
            with open("Template/nodeProperties/Valve_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            node_params["outlet_pressure"]["value"] = block["params"]["outlet_pressure"]["value"]
            with open("Template/processNodes/processNodes_Valve.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Mixer":
            with open("Template/nodeProperties/Mixer_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["outlet_pressure"]["value"] = block["params"]["outlet_pressure"]["value"]
            node_params["outlet_pressure"]["unit"] = block["params"]["outlet_pressure"]["unit"]
            node_params["no_inlets"]["value"] = block["params"]["no_inlets"]
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            with open("Template/processNodes/processNodes_Mixer.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            # Mixer的入口可以有多个 所以ports部分需要修改
            relateVirtualPortList = [
                {"id": "inlet_0", "name": "inlet", "relatedEntityId": "23cf3301-ecbe-4438-840d-ddf4539e6586",
                 "relatedEntityName": "inlet"}
            ]
            for i in range(len(block["in_streams"])):
                relateVirtualPortList.append(
                    {"id": f"inlet_{i+1}", "name": "虚拟桩", "relatedEntityId": "23cf3301-ecbe-4438-840d-ddf4539e6586",
                     "relatedEntityName": "inlet"}
                )
            node_data["ports"][0]["relateVirtualPortList"] = relateVirtualPortList
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "SSplit" or block["type"] == "FSplit":
            with open("Template/nodeProperties/Splitter_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["outlet_pressure"]["value"] = block["params"]["outlet_pressure"]["value"]
            node_params["outlet_pressure"]["unit"] = block["params"]["outlet_pressure"]["unit"]
            node_params["no_outlets"]["value"] = block["params"]["no_outlets"]
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            node_params["split_fraction"]["value"] = block["params"]["split_fraction_value"]
            node_params["split_fraction"]["rowHeader"] = block["params"]["split_fraction_rowHeader"]
            # rows数据还要保存对应的连线的 label
            rows = []
            rows_index = []
            for c in connect_info:
                block_id = map_of_id[id]
                if c["source"]["cell"] == block_id:
                    label = c["attrs"]["label"]
                    port = c["source"]["port"]
                    rows.append(label)
                    rows_index.append(port.rsplit('_', 1)[1])
            # 将两个列表配对，按第二个列表排序
            pairs = sorted(zip(rows, rows_index))
            # 解压排序后的结果
            sorted_rows, sorted_rows_index = zip(*pairs)
            node_params["split_fraction"]["rows"] = sorted_rows

            with open("Template/processNodes/processNodes_Splitter.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            # Splitter的出口可以有多个 所以ports部分需要修改
            relateVirtualPortList = [
                {"id": "outlet_0", "name": "outlet", "relatedEntityId": "e1fc9da2-489a-4c7e-8bc2-9dc82e1a5490", "relatedEntityName": "outlet" }
            ]
            for i in range(len(block["out_streams"])):
                relateVirtualPortList.append(
                    {"id": f"outlet_{i+1}", "name": "虚拟桩", "relatedEntityId": "e1fc9da2-489a-4c7e-8bc2-9dc82e1a5490", "relatedEntityName": "outlet" }
                )
            node_data["ports"][1]["relateVirtualPortList"] = relateVirtualPortList
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "HeatX":
            with open("Template/nodeProperties/HeatX_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["hot_outlet_pressure"]["value"] = block["params"]["hot_outlet_pressure"]["value"]
            node_params["hot_outlet_pressure"]["unit"] = block["params"]["hot_outlet_pressure"]["unit"]
            node_params["cold_outlet_pressure"]["value"] = block["params"]["cold_outlet_pressure"]["value"]
            node_params["cold_outlet_pressure"]["unit"] = block["params"]["cold_outlet_pressure"]["unit"]
            node_params["area"]["value"] = block["params"]["area"]["value"]
            node_params["area"]["unit"] = block["params"]["area"]["unit"]
            node_params["u_overall"]["value"] = block["params"]["u_overall"]["value"]
            node_params["u_overall"]["unit"] = block["params"]["u_overall"]["unit"].replace("Watt", "W")
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            with open("Template/processNodes/processNodes_HeatX.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "RadFrac":
            with open("Template/nodeProperties/Column_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            node_params["no_trays"]["value"] = block["params"]["no_trays"]["value"]
            node_params["no_total_trays"]["value"] = block["params"]["no_trays"]["value"]
            node_params["vapor_molar_composition_profile_guess"]["cloumnSize"] = block["params"]["no_trays"]["value"]
            node_params["liquid_molar_composition_profile_guess"]["cloumnSize"] = block["params"]["no_trays"]["value"]
            node_params["no_feeds"]["value"] = block["params"]["no_feeds"]
            node_params["feed_trays"]["value"] = block["params"]["feed_trays_value"]
            node_params["feed_trays"]["rows"] = block["params"]["feed_trays_rows"]
            node_params["feed_trays"]["rowSize"] = len(block["params"]["feed_trays_rows"])
            node_params["feed_trays"]["rowHeader"] = block["params"]["feed_trays_rowHeader"]
            # 设置侧线数量
            node_params["no_vapor_side_draw"]["value"] = len(block["params"]["vapor_side_draw"]["stream_name"])
            node_params["no_liquid_side_draw"]["value"] = len(block["params"]["liquid_side_draw"]["stream_name"])
            # 设置侧线的流股，塔板数和流量
            if len(block["params"]["vapor_side_draw"]["stream_name"]):
                node_params["vapor_side_draw_stages"]["value"] = block["params"]["vapor_side_draw"]["stages"]
                node_params["vapor_side_draw_stages"]["rows"] = block["params"]["vapor_side_draw"]["stream_name"]
                node_params["vapor_side_draw_stages"]["rowSize"] = len(block["params"]["vapor_side_draw"]["stream_name"])
                node_params["vapor_side_draw_molar_flowrate"]["rowSize"] = len(block["params"]["vapor_side_draw"]["stream_name"])
                node_params["vapor_side_draw_molar_flowrate"]["rows"] = block["params"]["vapor_side_draw"]["stream_name"]
                node_params["vapor_side_draw_molar_flowrate"]["value"] = block["params"]["vapor_side_draw"]["flow"]
            else:
                node_params["vapor_side_draw_stages"] = {"isKeyword": True}
                node_params["vapor_side_draw_flowrate_basis"] = {"isKeyword": True}
                node_params["vapor_side_draw_molar_flowrate"] = {"isKeyword": True,"unitType": "molar_flowrate"}
            if len(block["params"]["liquid_side_draw"]["stream_name"]):
                node_params["liquid_side_draw_stages"]["value"] = block["params"]["liquid_side_draw"]["stages"]
                node_params["liquid_side_draw_stages"]["rows"] = block["params"]["liquid_side_draw"]["stream_name"]
                node_params["liquid_side_draw_stages"]["rowSize"] = len(block["params"]["liquid_side_draw"]["stream_name"])
                node_params["liquid_side_draw_molar_flowrate"]["rowSize"] = len(
                    block["params"]["liquid_side_draw"]["stream_name"])
                node_params["liquid_side_draw_molar_flowrate"]["rows"] = block["params"]["liquid_side_draw"]["stream_name"]
                node_params["liquid_side_draw_molar_flowrate"]["value"] = block["params"]["liquid_side_draw"]["flow"]
            else:
                node_params["liquid_side_draw_stages"] = {"isKeyword": True}
                node_params["liquid_side_draw_flowrate_basis"] = {"isKeyword": True}
                node_params["liquid_side_draw_molar_flowrate"] = {"isKeyword": True, "unitType": "molar_flowrate"}
            # 若规定是组分分率 那么设置组分规定的数据,组分规定有0，1，2个，若个数为2，则两个都填写上去，若是个数为1，则第一个填写，第二个设置为塔顶采出摩尔流
            # 若两个都没有 则把回流比和塔顶采出摩尔流分别放在1，2位置
            if len(block["params"]["comp_spec"]["PEC_COMPS_index"]) >= 1:
                node_params["comp_spec_1_id"]["value"] = block["params"]["comp_spec"]["PEC_COMPS_index"][0]
                node_params["comp_spec_1_id"]["realValue"] = block["params"]["comp_spec"]["PEC_COMPS"][0]
                node_params["comp_spec_1_stage"]["value"] = block["params"]["comp_spec"]["SPEC_STREAMS"][0]
                node_params["comp_spec_1_phase"]["realValue"] = "0" if block["params"]["comp_spec"]["SPEC_PHASE"][0] == "V" else "1"
                node_params["comp_spec_1_phase"]["value"] = "0" if block["params"]["comp_spec"]["SPEC_PHASE"][0] == "V" else "1"
                # 先默认是摩尔的，后续需要修改 通过SPEC_TYPE字段来判断
                node_params["comp_spec_1_molar"]["value"] = block["params"]["comp_spec"]["SPEC_DESCRIP"][0]
                if len(block["params"]["comp_spec"]["PEC_COMPS_index"]) == 2:
                    node_params["comp_spec_2_id"]["value"] = block["params"]["comp_spec"]["PEC_COMPS_index"][1]
                    node_params["comp_spec_2_id"]["realValue"] = block["params"]["comp_spec"]["PEC_COMPS"][1]
                    node_params["comp_spec_2_stage"]["value"] = block["params"]["comp_spec"]["SPEC_STREAMS"][1]
                    node_params["comp_spec_2_phase"]["realValue"] = "0" if block["params"]["comp_spec"]["SPEC_PHASE"][
                                                                       1] == "V" else "1"
                    node_params["comp_spec_2_phase"]["value"] = "0" if block["params"]["comp_spec"]["SPEC_PHASE"][
                                                                   1] == "V" else "1"
                    # 先默认是摩尔的，后续需要修改 通过SPEC_TYPE字段来判断
                    node_params["comp_spec_2_molar"]["value"] = block["params"]["comp_spec"]["SPEC_DESCRIP"][1]
                else:
                    node_params["comp_spec_2_id"] = {"isKeyword": True}
                    node_params["comp_spec_2_stage"] = {"isKeyword": True}
                    node_params["comp_spec_2_phase"] = {"isKeyword": True}
                    node_params["top_product_molar_flowrate"] = {
                        "isKeyword": True,
                        "fixed": True,
                        "unitType": "molar_flowrate",
                        "value": 0,
                        "unit": "mol/s"
                    }
                    node_params["top_product_molar_flowrate"]["value"] = block["params"]["top_molar_flowrate_guess"]["value"]
                # 设置初值：回流比/塔顶采出流量初值
                node_params["reflux_ratio_guess"]["value"] = block["params"]["reflux_ratio_guess"]["value"]  # 摩尔回流比初值
                node_params["top_molar_flowrate_guess"]["value"] = block["params"]["top_molar_flowrate_guess"][
                    "value"]  # 塔顶采出摩尔流量初值

            # 设置冷凝器类型
            if block["params"]["CONDENSER"]["value"] == "PARTIAL-V-L": # 分凝
                node_params["condenser_type"]["value"] = "1"
                node_params["condenser_type"]["realValue"] = "1"
                node_params["top_molar_vapor_fraction"]["value"] = block["params"]["top_vapor_fraction"]["value"]
                node_params["top_molar_vapor_fraction"]["fixed"] = True
            elif block["params"]["CONDENSER"]["value"] == "TOTAL":
                node_params["condenser_type"]["value"] = "0"
                node_params["condenser_type"]["realValue"] = "0"
                # node_params["top_vapor_fraction"]["fixed"] = False
            elif block["params"]["CONDENSER"]["value"] == "PARTIAL-V":
                node_params["condenser_type"]["value"] = "1"
                node_params["condenser_type"]["realValue"] = "1"
                node_params["top_molar_vapor_fraction"]["value"] = 1
                node_params["top_molar_vapor_fraction"]["fixed"] = True
            node_params["tray_1_pressure"]["value"] = block["params"]["tray_1_pressure"]["value"]
            node_params["tray_2_pressure"]["value"] = block["params"]["tray_2_pressure"]["value"]
            node_params["tray_pressure_drop"]["value"] = block["params"]["tray_pressure_drop"]["value"]
            node_params["tray_1_pressure"]["unit"] = block["params"]["tray_1_pressure"]["unit"]
            node_params["tray_2_pressure"]["unit"] = block["params"]["tray_2_pressure"]["unit"]
            node_params["tray_pressure_drop"]["unit"] = block["params"]["tray_pressure_drop"]["unit"]
            node_params["tray_pressure"]["value"] = block["params"]["tray_pressure"]
            with open("Template/processNodes/processNodes_Column.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            # 精馏塔的的入口可以有多个 所以ports部分需要修改
            relateVirtualPortList_in = [
                {"id": "feed_in_0", "name": "feed_in", "relatedEntityId": "8224b29c-499c-49cf-80ef-b1d3c6038a36", "relatedEntityName": "feed_in"}
            ]
            for i in range(len(block["in_streams"])):
                relateVirtualPortList_in.append(
                    {"id": f"feed_in_{i + 1}", "name": "虚拟桩",
                        "relatedEntityId": "8224b29c-499c-49cf-80ef-b1d3c6038a36", "relatedEntityName": "feed_in"}
                )
            # 精馏塔的侧线 若有多个也需要修改
            relateVirtualPortList_L_out = [
                {
                    "id": "liquid_side_draw_0",
                    "name": "liquid_side_draw",
                    "relatedEntityId": "126461b6-f46d-4a6e-ad30-9d6da0a749a9",
                    "relatedEntityName": "liquid_side_draw"
                }
            ]
            for i in range(len(block["params"]["liquid_side_draw"]["stream_name"])):
                relateVirtualPortList_L_out.append(
                    {"id": f"liquid_side_draw_{i + 1}", "name": "虚拟桩",
                     "relatedEntityId": "126461b6-f46d-4a6e-ad30-9d6da0a749a9", "relatedEntityName": "liquid_side_draw"}
                )
            relateVirtualPortList_V_out = [
                {
                    "id": "vapor_side_draw_0",
                    "name": "虚拟桩",
                    "relatedEntityId": "1323f78d-6949-400b-a456-1ee3241e8133",
                    "relatedEntityName": "vapor_side_draw"
                }
            ]
            for i in range(len(block["params"]["vapor_side_draw"]["stream_name"])):
                relateVirtualPortList_V_out.append(
                    {
                        "id": "vapor_side_draw_{i + 1}",
                        "name": "虚拟桩",
                        "relatedEntityId": "1323f78d-6949-400b-a456-1ee3241e8133",
                        "relatedEntityName": "vapor_side_draw"
                    }
                )
            node_data["ports"][0]["relateVirtualPortList"] = relateVirtualPortList_in
            node_data["ports"][4]["relateVirtualPortList"] = relateVirtualPortList_V_out
            node_data["ports"][5]["relateVirtualPortList"] = relateVirtualPortList_L_out
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))
        elif block["type"] == "Sep":
            with open("Template/nodeProperties/ComponentSplitter_properties.json", 'r', encoding='utf-8') as f:
                node_params = json.load(f)
            node_params["comp_num"]["value"] = block["params"]["comp_nums"]
            node_params["no_outlets"]["value"] = block["params"]["no_outlets"]
            node_params["split_fractions"]["value"] = block["params"]["split_fractions_value"]
            node_params["split_fractions"]["rowHeader"] = block["params"]["split_fractions_rowHeader"]
            node_params["split_fractions"]["colHeader"] = block["params"]["split_fractions_colHeader"]
            node_params["split_fractions"]["cols"] = block["params"]["split_fractions_cols"]
            # rows数据还要保存对应的连线的 label
            rows = []
            rows_index = []
            for c in connect_info:
                block_id = map_of_id[id]
                if c["source"]["cell"] == block_id:
                    label = c["attrs"]["label"]
                    port = c["source"]["port"]
                    rows.append(label)
                    rows_index.append(port.rsplit('_', 1)[1])
            # 将两个列表配对，按第二个列表排序
            pairs = sorted(zip(rows, rows_index))
            # 解压排序后的结果
            sorted_rows, sorted_rows_index = zip(*pairs)
            node_params["split_fractions"]["rows"] = sorted_rows
            with open("Template/processNodes/processNodes_ComponentSplitter.json", 'r', encoding='utf-8') as f:
                node_data = json.load(f)
            node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
            node_data["id"] = map_of_id[id]
            for node in input_data["processGraph"]["nodes"]:
                if id == node["id"]:
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    break
            # 组分分离器的出口可以有多个 所以ports部分需要修改
            relateVirtualPortList = [
                {"id": "outlet_0", "name": "outlet", "relatedEntityId": "fb0dfbb1-6b03-4102-8e08-2b4f6852522f", "relatedEntityName": "outlet"}
            ]
            for i in range(len(block["out_streams"])):
                relateVirtualPortList.append(
                    {"id": f"outlet_{i + 1}", "name": "虚拟桩",
                        "relatedEntityId": "fb0dfbb1-6b03-4102-8e08-2b4f6852522f", "relatedEntityName": "outlet"}
                )
            node_data["ports"][1]["relateVirtualPortList"] = relateVirtualPortList
            node_data["data"]["label"] = id
            result.append(copy.deepcopy(node_data))

    for id, stream in input_data["streams"].items():
        for node in input_data["processGraph"]["nodes"]:
            # 证明当前的流股要不是Sink 要不是 Source
            if id == node["id"]:
                if node["type"] == "Sink":
                    with open("Template/nodeProperties/Sink_properties.json", 'r', encoding='utf-8') as f:
                        node_params = json.load(f)
                    with open("Template/processNodes/processNodes_Sink.json", 'r', encoding='utf-8') as f:
                        node_data = json.load(f)
                    node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
                    node_data["id"] = map_of_id[id]
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    node_data["data"]["label"] = id
                    result.append(copy.deepcopy(node_data))
                elif node["type"] == "Source":
                    with open("Template/nodeProperties/Source_properties.json", 'r', encoding='utf-8') as f:
                        node_params = json.load(f)
                    node_params["molar_compositions"]["value"] = list(stream["composition_mole_frac"].values())
                    node_params["molar_compositions"]["rowHeader"] = input_data["components"]["top_name"]
                    node_params["molar_compositions"]["rows"] = input_data["components"]["top_name"]
                    if stream["properties"]["mole_flow"]["unit"] == "kmol/sec":
                        node_params["molar_flowrate"]["value"] = stream["properties"]["mole_flow"]["value"] * 1000
                    else:
                        if "sec" in stream["properties"]["mole_flow"]["unit"]:
                            stream["properties"]["mole_flow"]["unit"] = stream["properties"]["mole_flow"]["unit"].replace("sec","s")
                        node_params["molar_flowrate"]["value"] = stream["properties"]["mole_flow"]["value"]
                        node_params["molar_flowrate"]["unit"] = stream["properties"]["mole_flow"]["unit"]
                    node_params["pressure"]["value"] = stream["properties"]["pressure"]["value"]
                    node_params["pressure"]["unit"] = stream["properties"]["pressure"]["unit"]
                    node_params["temperature"]["value"] = stream["properties"]["temperature"]["value"]
                    node_params["temperature"]["unit"] = stream["properties"]["temperature"]["unit"]
                    node_params["comp_num"]["value"] = len(list(stream["composition_mole_frac"].values()))
                    with open("Template/processNodes/processNodes_Source.json", 'r', encoding='utf-8') as f:
                        node_data = json.load(f)
                    node_data["nodeProperties"] = json.dumps(node_params, ensure_ascii=False)
                    node_data["id"] = map_of_id[id]
                    node_data["x"] = node["x"]
                    node_data["y"] = node["y"]
                    node_data["data"]["label"] = id
                    result.append(copy.deepcopy(node_data))

    return result

template_map_type2id = {
    "Flash2": "598fddf9",
    "Mixer": "851a7777",
    "Heater": "c4cecd0c",
    "Compr": "8c7245c0",
    "SSplit": "03f69f8d",
    "FSplit": "03f69f8d",
    "Source": "54a52706",
    "Sink": "ff1924d5",
    "HeatX": "795f07b5",
    "Valve": "df08bcf0",
    "Pump": "3988f609",
    "RadFrac": "deb7b0aa",
    "Sep": "69ad4ad5",
    "RecycleBreaker": "03a1aed2",
    "RStoic": "b0bd232c"
}

# 辅助生成ID
def generate_aspen_id(input_data):
    map_of_id = {}
    flash_index = 1
    heater_index = 1
    compr_index = 1
    mixer_index = 1
    splitter_index = 1
    heatX_index = 1
    column_index = 1
    valve_index = 1
    sep_index = 1
    pump_index = 1
    source_index = 1
    sink_index = 1
    recycle_index = 1
    reactorConversion_index = 1
    for blockName, blockInfo in input_data["blocks"].items():
        # 生成16位十六进制数（小写）
        hex_part1 = ""
        hex_part2 = ''.join(random.choices('0123456789abcdef', k=8))
        final_name = ""
        if blockInfo["type"] == "Flash2":
            hex_part1 = template_map_type2id["Flash2"]
            final_name = f"Flash{flash_index}"
            flash_index += 1
        elif blockInfo["type"] == "Heater":
            hex_part1 = template_map_type2id["Heater"]
            final_name = f"Heater{heater_index}"
            heater_index += 1
        elif blockInfo["type"] == "Valve":
            hex_part1 = template_map_type2id["Valve"]
            final_name = f"Valve{valve_index}"
            valve_index += 1
        elif blockInfo["type"] == "Compr":
            hex_part1 = template_map_type2id["Compr"]
            final_name = f"Compressor{compr_index}"
            compr_index += 1
        elif blockInfo["type"] == "Pump":
            hex_part1 = template_map_type2id["Pump"]
            final_name = f"Pump{pump_index}"
            pump_index += 1
        elif blockInfo["type"] == "Mixer":
            hex_part1 = template_map_type2id["Mixer"]
            final_name = f"Mixer{mixer_index}"
            mixer_index += 1
        elif blockInfo["type"] == "SSplit":
            hex_part1 = template_map_type2id["SSplit"]
            final_name = f"Splitter{splitter_index}"
            splitter_index += 1
        elif blockInfo["type"] == "FSplit":
            hex_part1 = template_map_type2id["FSplit"]
            final_name = f"Splitter{splitter_index}"
            splitter_index += 1
        elif blockInfo["type"] == "HeatX":
            hex_part1 = template_map_type2id["HeatX"]
            final_name = f"HeatExchanger{heatX_index}"
            heatX_index += 1
        elif blockInfo["type"] == "RadFrac":
            hex_part1 = template_map_type2id["RadFrac"]
            final_name = f"DistillationColumn2{column_index}"
            column_index += 1
        elif blockInfo["type"] == "Sep":
            hex_part1 = template_map_type2id["Sep"]
            final_name = f"ComponentSplitter{sep_index}"
            sep_index += 1
        elif blockInfo["type"] == "RecycleBreaker":
            hex_part1 = template_map_type2id["RecycleBreaker"]
            final_name = f"RecycleBreaker{recycle_index}"
            recycle_index += 1
        elif blockInfo["type"] == "RStoic":
            hex_part1 = template_map_type2id["RStoic"]
            final_name = f"ReactorConversion{reactorConversion_index}"
            reactorConversion_index += 1
        map_of_id[blockName] = f"{hex_part1}_{hex_part2}_{final_name}"
    for streamName in input_data["streams"].keys():
        # 生成16位十六进制数（小写）
        hex_part1 = ''.join(random.choices('0123456789abcdef', k=8))
        hex_part2 = ''.join(random.choices('0123456789abcdef', k=8))
        final_name = ""
        for node in input_data["processGraph"]["nodes"]:
            # 证明当前的流股要不是Sink 要不是 Source
            if streamName == node["id"]:
                if node["type"] == "Sink":
                    hex_part1 = template_map_type2id["Sink"]
                    final_name = f"Sink{sink_index}"
                    sink_index += 1
                elif node["type"] == "Source":
                    hex_part1 = template_map_type2id["Source"]
                    final_name = f"Source{source_index}"
                    source_index += 1
                else:
                    final_name = streamName
        map_of_id[streamName] = f"{hex_part1}_{hex_part2}_{final_name}"
    return map_of_id


# 用于处理连接的,写清楚拓扑结构
def extract_connections(modules_data):
    """
    从模块数据中提取连接拓扑结构（支持端口信息）

    Args:
        modules_data: 包含所有模块信息的字典，in_streams/out_streams是字典列表

    Returns:
        list: 连接关系列表，每个元素包含connect, from, from_port, to, to_port
    """
    connections = []

    # 第一步：建立流股到（模块，端口）的映射
    stream_sources = {}  # 流股 -> (来源模块, 来源端口)
    stream_destinations = {}  # 流股 -> (目标模块, 目标端口)

    # 遍历所有模块
    for module_name, module_info in modules_data.items():
        # 处理入口流股（目标端口）
        for in_port_dict in module_info.get("in_streams", []):
            for port_name, stream_name in in_port_dict.items():
                if stream_name not in stream_destinations:
                    stream_destinations[stream_name] = []
                stream_destinations[stream_name].append((module_name, port_name))

        # 处理出口流股（来源端口）
        for out_port_dict in module_info.get("out_streams", []):
            for port_name, stream_name in out_port_dict.items():
                if stream_name not in stream_sources:
                    stream_sources[stream_name] = []
                stream_sources[stream_name].append((module_name, port_name))

    # 第二步：收集所有流股
    all_streams = set()
    all_streams.update(stream_sources.keys())
    all_streams.update(stream_destinations.keys())

    # 第三步：为每个流股建立连接关系
    for stream in all_streams:
        connection = {"connect": stream}

        # 确定来源 (from 和 from_port)
        if stream in stream_sources:
            # 流股有来源模块
            if len(stream_sources[stream]) == 1:
                from_module, from_port = stream_sources[stream][0]
                connection["from"] = from_module
                connection["from_port"] = from_port
            else:
                # 多个来源（分流情况），这里简化处理，取第一个
                from_module, from_port = stream_sources[stream][0]
                connection["from"] = from_module
                connection["from_port"] = from_port
                print(f"警告: 流股 {stream} 有多个来源，只取第一个: {stream_sources[stream]}")
        else:
            # 没有来源模块，from设为流股自身，端口固定为outlet_0
            connection["from"] = stream
            connection["from_port"] = "outlet_0"

        # 确定去向 (to 和 to_port)
        if stream in stream_destinations:
            # 流股有目标模块
            if len(stream_destinations[stream]) == 1:
                to_module, to_port = stream_destinations[stream][0]
                connection["to"] = to_module
                connection["to_port"] = to_port
            else:
                # 多个去向（合流情况），这里简化处理，取第一个
                to_module, to_port = stream_destinations[stream][0]
                connection["to"] = to_module
                connection["to_port"] = to_port
                print(f"警告: 流股 {stream} 有多个去向，只取第一个: {stream_destinations[stream]}")
        else:
            # 没有目标模块，to设为流股自身，端口固定为inlet_0
            connection["to"] = stream
            connection["to_port"] = "inlet_0"

        connections.append(connection)

    return connections


###########################################
#######  componentList 读取对应的模板后只需要设置projectId即可
####### indexNew 和 indexOld 也得修改
###########################################
def create_componentList(input_data, projectId):
    componentList_result = []
    components = input_data["components"]["cas"]
    indexNew = 2
    indexOld = 1
    for c_name in components:
        """根据名称加载对应的JSON文件"""
        filename = f"{c_name}.json"
        with open(f"Template/component/{filename}", 'r', encoding='utf-8') as f:
            component_read = json.load(f)
        component_template = copy.deepcopy(component_read)
        component_template["id"] = ChemicalMapper.CHEMICAL_MAP[c_name]
        component_template["projectId"] = projectId
        component_template["indexNew"] = indexNew
        component_template["indexOld"] = indexOld
        indexNew += 1
        indexOld += 1
        componentList_result.append(component_template)
    return componentList_result


###########################################
#######  componentGroupPrivateList 目前默认写死 只改变projectId
###########################################
def create_componentGroupPrivateList(projectId, componentGroupId):
    componentGroupPrivateList_result = []
    with open("Template/componentGroupPrivateList/global.json", 'r', encoding='utf-8') as f:
        global_template = json.load(f)
    global_template["projectId"] = projectId
    global_template["id"] = componentGroupId
    componentGroupPrivateList_result.append(global_template)
    return componentGroupPrivateList_result


# 生成componentGroupId或者是methodPrivateList里面的id
def generate_secure_nineteen(length=19):
    """生成安全的随机数字字符串"""
    if length < 1:
        raise ValueError("长度必须大于0")

    digits = '0123456789'

    # 第一位不能是0
    first_digit = secrets.choice('123456789')

    # 生成剩余位数
    if length > 1:
        remaining = ''.join(secrets.choice(digits) for _ in range(length - 1))
        return first_digit + remaining

    return first_digit


###########################################
#######  componentGroupDetailPrivateList  只需要修改index
###########################################
def create_componentGroupDetailPrivateList(input_data, componentGroupId):
    componentGroupDetailPrivateList_result = []
    components = input_data["components"]["cas"]
    index = 1
    for c_name in components:
        """根据名称加载对应的JSON文件"""
        filename = f"{c_name}.json"
        with open(f"Template/componentPrivate/{filename}", 'r', encoding='utf-8') as f:
            component_read = json.load(f)
        component_template = copy.deepcopy(component_read)
        component_template["index"] = index
        index += 1
        component_template["componentGroupId"] = componentGroupId
        component_template["componentId"] = ChemicalMapper.CHEMICAL_MAP[c_name]
        componentGroupDetailPrivateList_result.append(component_template)
    return componentGroupDetailPrivateList_result


###########################################
#######  methodPrivateList  只需要修改projectId
###########################################
def create_methodPrivateList(input_data, projectId, methodId):
    methodPrivateList_result = []
    methad_name = input_data["methad"]
    """根据名称加载对应的JSON文件"""
    filename = f"{methad_name}.json"
    with open(f"Template/methodPrivateList/{filename}", 'r', encoding='utf-8') as f:
        methad_template = json.load(f)
    methad_template["projectId"] = projectId
    methad_template["id"] = "2020041427883515905" # 这里写死 保证和methodAlgoList/methodFreewaterList里面模板一样的id
    methodPrivateList_result.append(methad_template)
    return methodPrivateList_result


###########################################
#######  methodFreewaterList
###########################################


###########################################
#######  汇总
###########################################
def create_json():
    # 读取输入JSON
    with open("aspen_fixed_data.json", 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    with open("Template/final_template.json", 'r', encoding='utf-8') as f:
        final_result = json.load(f)
    map_of_id = generate_aspen_id(input_data)

    # 生成流程id和projectID
    processId = generate_projectId()
    projectId = generate_projectId()
    groupId = generate_projectId()
    componentGroupId = generate_secure_nineteen()
    methodId = generate_secure_nineteen()

    result_omProcessGraph = create_omProcessGraph(input_data, map_of_id, projectId, processId)
    final_result["omProcessGraph"] = result_omProcessGraph
    result_componentGroupDetailPrivateList = create_componentGroupDetailPrivateList(input_data, componentGroupId)
    final_result["componentGroupDetailPrivateList"] = result_componentGroupDetailPrivateList
    result_componentGroupPrivateList = create_componentGroupPrivateList(projectId, componentGroupId)
    final_result["componentGroupPrivateList"] = result_componentGroupPrivateList
    result_componentList = create_componentList(input_data, projectId)
    final_result["componentList"] = result_componentList
    result_methodPrivateList = create_methodPrivateList(input_data, projectId, methodId)
    final_result["methodPrivateList"] = result_methodPrivateList
    result_omProject = create_omProject(projectId)
    final_result["omProject"] = result_omProject
    result_omProcessArchive = create_omProcessArchive(projectId, processId)
    final_result["omProcessArchive"] = result_omProcessArchive
    with open("final_result.json", 'w', encoding='utf-8') as f:
        json.dump(final_result, f, indent=4, ensure_ascii=False)

    print(f"✨ 导出完成！")

    process_edges = create_omProcessGraph_processEdges(input_data, map_of_id)
    with open("process_edges.json", 'w', encoding='utf-8') as f:
        json.dump(process_edges, f, indent=4, ensure_ascii=False)

    process_nodes = create_omProcessGraph_processNodes(input_data, map_of_id, process_edges)
    with open("process_nodes.json", 'w', encoding='utf-8') as f:
        json.dump(process_nodes, f, indent=4, ensure_ascii=False)

    print(f"转换完成: {len(process_nodes)} 个节点, {len(process_edges)} 条边")



# 使用示例
if __name__ == "__main__":
    create_json()
    print(f"✨ 导出完成！")
