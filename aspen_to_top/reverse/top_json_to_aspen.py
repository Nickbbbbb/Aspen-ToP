import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.chemical_mapper import ChemicalMapper


TOP_TO_ASPEN_TYPE = {
    "Flash": "Flash2",
    "Heater": "Heater",
    "Compressor": "Compr",
    "Pump": "Pump",
    "Valve": "Valve",
    "Mixer": "Mixer",
    "Splitter": "FSplit",
    "HeatExchanger": "HeatX",
    "DistillationColumn": "RadFrac",
    "ComponentSplitter": "Sep",
    "RecycleBreaker": "RecycleBreaker",
    "ReactorConversion": "RStoic",
}


class TopJsonToAspenExtractor:
    """Recover a normalized Aspen-like JSON structure from ToP JSON/HSS.

    Important boundary:
    - This class restores the same *intermediate* data shape used by the
      forward BKP -> HSS pipeline.
    - It does not directly create an Aspen .bkp archive. Writing .bkp still
      requires Aspen COM automation that rebuilds the simulation model.
    """

    def from_hss(self, hss_file: str, output_json: Optional[str] = None) -> Dict[str, Any]:
        from ..encryption.hss_tool import HssTool

        hss_path = Path(hss_file).resolve()
        if not hss_path.exists():
            raise FileNotFoundError(f"HSS file not found: {hss_path}")

        target_json = Path(output_json).resolve() if output_json else hss_path.with_suffix(".recovered.extracted.json")
        temp_json = target_json.with_suffix(".decrypted.json")
        HssTool.decrypt(str(hss_path), str(temp_json))
        data = self.from_top_json(str(temp_json), output_json=str(target_json))
        return data

    def from_top_json(self, input_json: str, output_json: Optional[str] = None) -> Dict[str, Any]:
        input_path = Path(input_json).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"ToP JSON file not found: {input_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            top_data = json.load(handle)

        result = self._convert(top_data)

        if output_json:
            output_path = Path(output_json).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=4, ensure_ascii=False)

        return result

    def _convert(self, top_data: Dict[str, Any]) -> Dict[str, Any]:
        process_graph = top_data.get("omProcessGraph") or {}
        nodes = self._loads_json_array(process_graph.get("processNodes"))
        edges = self._loads_json_array(process_graph.get("processEdges"))

        node_by_id = {node.get("id"): node for node in nodes}
        label_by_id = {
            node_id: self._node_label(node)
            for node_id, node in node_by_id.items()
        }

        components = self._build_components(top_data)
        method = self._build_method(top_data)
        process_graph_data = self._build_process_graph(nodes, edges)
        blocks, streams, stream_topology_map = self._build_blocks_and_streams(
            nodes, edges, label_by_id, components
        )

        return {
            "components": components,
            "blocks": blocks,
            "streams": streams,
            "params": {},
            "methad": method,
            "stream_topology_map": stream_topology_map,
            "processGraph": process_graph_data,
        }

    def _build_components(self, top_data: Dict[str, Any]) -> Dict[str, List[Any]]:
        component_list = top_data.get("componentList") or []
        labels = []
        formulas = []
        cas_numbers = []
        aspen_names = []
        top_names = []

        for component in component_list:
            label = self._first_real_value(
                component.get("label"),
                component.get("alias"),
                component.get("name"),
                component.get("formula"),
            )
            formula = self._first_real_value(component.get("formula"), label)
            cas = self._first_real_value(component.get("cas"))
            top_name = self._first_real_value(component.get("name"), component.get("label"), component.get("alias"), label)

            mapping = None
            for candidate in (label, component.get("alias"), component.get("name"), top_name):
                if candidate:
                    mapping = ChemicalMapper.get_by_aspen_name(str(candidate))
                    if mapping:
                        break

            labels.append(label)
            formulas.append(mapping["aspen_formula"] if mapping else formula)
            cas_numbers.append(cas)
            aspen_names.append(mapping["aspen_name"] if mapping else label)
            top_names.append(top_name)

        return {
            "fenzi": formulas,
            "label": labels,
            "cas": cas_numbers,
            "aspen_name": aspen_names,
            "top_name": top_names,
        }

    def _build_method(self, top_data: Dict[str, Any]) -> str:
        method_list = top_data.get("methodPrivateList") or []
        if not method_list:
            return ""
        return method_list[0].get("baseAlgo", "") or ""

    def _build_process_graph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        graph_nodes = []
        id_to_label = {node.get("id"): self._node_label(node) for node in nodes}

        for node in nodes:
            node_type = node.get("type")
            label = self._node_label(node)
            entry = {
                "id": label,
                "type": TOP_TO_ASPEN_TYPE.get(node_type, node_type),
                "data": {"label": label},
                "x": node.get("x", 0),
                "y": node.get("y", 0),
            }
            if node_type in ("Source", "Sink"):
                entry["type"] = node_type
            graph_nodes.append(entry)

        graph_edges = []
        for edge in edges:
            graph_edges.append({
                "source": id_to_label.get(edge.get("source", {}).get("cell"), ""),
                "target": id_to_label.get(edge.get("target", {}).get("cell"), ""),
                "label": edge.get("attrs", {}).get("label", ""),
            })

        return {"nodes": graph_nodes, "edges": graph_edges}

    def _build_blocks_and_streams(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        label_by_id: Dict[str, str],
        components: Dict[str, List[Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        blocks: Dict[str, Any] = {}
        streams: Dict[str, Any] = {}
        stream_topology_map: Dict[str, Any] = {}

        component_labels = components.get("label", [])
        component_top_names = components.get("top_name", [])
        label_to_top_name = {
            label: component_top_names[index]
            for index, label in enumerate(component_labels)
            if index < len(component_top_names)
        }

        source_stream_props: Dict[str, Dict[str, Any]] = {}
        source_nodes = {
            self._node_label(node): node
            for node in nodes
            if node.get("type") == "Source"
        }
        for stream_name, node in source_nodes.items():
            props = json.loads(node.get("nodeProperties", "{}"))
            source_stream_props[stream_name] = self._restore_source_stream(props, label_to_top_name)

        for node in nodes:
            node_type = node.get("type")
            if node_type in ("Source", "Sink"):
                continue

            block_name = self._node_label(node)
            node_props = json.loads(node.get("nodeProperties", "{}"))
            aspen_type = TOP_TO_ASPEN_TYPE.get(node_type)
            if not aspen_type:
                continue

            blocks[block_name] = {
                "type": aspen_type,
                "in_streams": [],
                "out_streams": [],
                "params": self._restore_block_params(node_type, node_props),
            }

        for edge in edges:
            stream_name = edge.get("attrs", {}).get("label", "")
            source_id = edge.get("source", {}).get("cell")
            target_id = edge.get("target", {}).get("cell")
            source_port = edge.get("source", {}).get("port")
            target_port = edge.get("target", {}).get("port")
            source_label = label_by_id.get(source_id, "")
            target_label = label_by_id.get(target_id, "")
            source_node = self._safe_lookup(nodes, source_id)
            target_node = self._safe_lookup(nodes, target_id)

            if source_node and source_node.get("type") not in ("Source", "Sink") and source_label in blocks:
                blocks[source_label]["out_streams"].append({source_port: stream_name})
            if target_node and target_node.get("type") not in ("Source", "Sink") and target_label in blocks:
                blocks[target_label]["in_streams"].append({target_port: stream_name})

            source_block_name = None if source_node and source_node.get("type") == "Source" else source_label
            target_block_name = None if target_node and target_node.get("type") == "Sink" else target_label

            stream_topology_map[stream_name] = {
                "source": source_block_name,
                "dest": target_block_name,
            }

            stream_record = streams.setdefault(stream_name, self._empty_stream_record())
            stream_record["connection"] = {
                "from": source_block_name,
                "to": target_block_name,
            }

            if source_node and source_node.get("type") == "Source":
                source_record = source_stream_props.get(stream_name, self._empty_stream_record())
                stream_record["properties"] = source_record.get("properties", stream_record["properties"])
                stream_record["composition_mole_frac"] = source_record.get(
                    "composition_mole_frac",
                    stream_record["composition_mole_frac"],
                )

        for block in blocks.values():
            block["in_streams"] = self._sort_port_maps(block.get("in_streams", []))
            block["out_streams"] = self._sort_port_maps(block.get("out_streams", []))

        self._fill_missing_stream_compositions(streams, component_labels)
        return blocks, streams, stream_topology_map

    @staticmethod
    def _restore_block_params(node_type: str, node_props: Dict[str, Any]) -> Dict[str, Any]:
        comp_num = TopJsonToAspenExtractor._prop_value(node_props, "comp_num", 0)

        if node_type == "Flash":
            thermal_spec = str(TopJsonToAspenExtractor._prop_value(node_props, "Thermal_specification", "0"))
            spec_opt = "PV" if thermal_spec == "1" else "TP"
            return {
                "SPEC_OPT": {"value": spec_opt, "unit": ""},
                "system_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "system_pressure"),
                "comp_nums": comp_num,
                "system_temperature": TopJsonToAspenExtractor._prop_dict(node_props, "system_temperature"),
                "system_vapor_molar_fraction": TopJsonToAspenExtractor._prop_dict(node_props, "system_vapor_molar_fraction"),
                "system_heat_duty": TopJsonToAspenExtractor._prop_dict(node_props, "system_heat_duty"),
            }

        if node_type == "Heater":
            return {
                "outlet_stream_temperature": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_stream_temperature"),
                "comp_nums": comp_num,
                "outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_pressure"),
            }

        if node_type == "Compressor":
            return {
                "outlet_stream_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_stream_pressure"),
                "comp_nums": comp_num,
                "isentropic_efficiency": TopJsonToAspenExtractor._prop_dict(node_props, "isentropic_efficiency"),
                "mechanical_efficiency": TopJsonToAspenExtractor._prop_dict(node_props, "mechanical_efficiency"),
            }

        if node_type == "Pump":
            outlet_spec = str(TopJsonToAspenExtractor._prop_value(node_props, "outlet_specification", "0"))
            opt_spec = "DELP" if outlet_spec == "1" else "PRES"
            return {
                "OPT_SPEC": {"value": opt_spec, "unit": ""},
                "outlet_stream_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_stream_pressure"),
                "pressure_increase": TopJsonToAspenExtractor._prop_dict(node_props, "pressure_increase"),
                "pressure_ratio": TopJsonToAspenExtractor._prop_dict(node_props, "pressure_ratio"),
                "total_power": TopJsonToAspenExtractor._prop_dict(node_props, "total_power"),
                "comp_nums": comp_num,
                "pumping_efficiency": TopJsonToAspenExtractor._prop_dict(node_props, "pumping_efficiency"),
            }

        if node_type == "Valve":
            return {
                "comp_nums": comp_num,
                "outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_pressure"),
            }

        if node_type == "Mixer":
            return {
                "outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_pressure"),
                "comp_nums": comp_num,
                "no_inlets": TopJsonToAspenExtractor._prop_value(node_props, "no_inlets", 0),
            }

        if node_type == "Splitter":
            return {
                "outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "outlet_pressure"),
                "comp_nums": comp_num,
                "no_outlets": TopJsonToAspenExtractor._prop_value(node_props, "no_outlets", 0),
                "split_fraction_value": TopJsonToAspenExtractor._prop_value(node_props, "split_fraction", []),
                "split_fraction_rows": TopJsonToAspenExtractor._prop_rows(node_props, "split_fraction"),
                "split_fraction_rowHeader": TopJsonToAspenExtractor._prop_row_header(node_props, "split_fraction"),
            }

        if node_type == "ComponentSplitter":
            return {
                "comp_nums": comp_num,
                "no_outlets": TopJsonToAspenExtractor._prop_value(node_props, "no_outlets", 0),
                "split_fractions_value": TopJsonToAspenExtractor._prop_value(node_props, "split_fractions", []),
                "split_fractions_rows": TopJsonToAspenExtractor._prop_rows(node_props, "split_fractions"),
                "split_fractions_rowHeader": TopJsonToAspenExtractor._prop_row_header(node_props, "split_fractions"),
                "split_fractions_cols": TopJsonToAspenExtractor._prop_cols(node_props, "split_fractions"),
                "split_fractions_colHeader": TopJsonToAspenExtractor._prop_col_header(node_props, "split_fractions"),
            }

        if node_type == "HeatExchanger":
            return {
                "hot_outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "hot_outlet_pressure"),
                "cold_outlet_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "cold_outlet_pressure"),
                "comp_nums": comp_num,
                "area": TopJsonToAspenExtractor._prop_dict(node_props, "area"),
                "u_overall": TopJsonToAspenExtractor._prop_dict(node_props, "u_overall"),
            }

        if node_type == "DistillationColumn":
            return {
                "comp_nums": comp_num,
                "CONDENSER": {"value": TopJsonToAspenExtractor._restore_condenser(node_props), "unit": ""},
                "no_trays": TopJsonToAspenExtractor._prop_dict(node_props, "no_trays"),
                "feed_trays_value": TopJsonToAspenExtractor._prop_value(node_props, "feed_trays", []),
                "feed_trays_rows": TopJsonToAspenExtractor._prop_rows(node_props, "feed_trays"),
                "feed_trays_rowHeader": TopJsonToAspenExtractor._prop_row_header(node_props, "feed_trays"),
                "no_feeds": TopJsonToAspenExtractor._prop_value(node_props, "no_feeds", 0),
                "vapor_side_draw": {
                    "stream_name": TopJsonToAspenExtractor._prop_rows(node_props, "vapor_side_draw_stages"),
                    "stages": TopJsonToAspenExtractor._prop_value(node_props, "vapor_side_draw_stages", []),
                    "flow": TopJsonToAspenExtractor._prop_value(node_props, "vapor_side_draw_molar_flowrate", []),
                    "flow_unit": TopJsonToAspenExtractor._prop_unit(node_props, "vapor_side_draw_molar_flowrate", "mol/s"),
                },
                "liquid_side_draw": {
                    "stream_name": TopJsonToAspenExtractor._prop_rows(node_props, "liquid_side_draw_stages"),
                    "stages": TopJsonToAspenExtractor._prop_value(node_props, "liquid_side_draw_stages", []),
                    "flow": TopJsonToAspenExtractor._prop_value(node_props, "liquid_side_draw_molar_flowrate", []),
                    "flow_unit": TopJsonToAspenExtractor._prop_unit(node_props, "liquid_side_draw_molar_flowrate", "mol/s"),
                },
                "top_vapor_fraction": TopJsonToAspenExtractor._prop_dict(node_props, "top_molar_vapor_fraction"),
                "top_molar_flowrate_guess": TopJsonToAspenExtractor._prop_dict(node_props, "top_molar_flowrate_guess"),
                "reflux_ratio_guess": TopJsonToAspenExtractor._prop_dict(node_props, "reflux_ratio_guess"),
                "tray_1_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "tray_1_pressure"),
                "tray_2_pressure": TopJsonToAspenExtractor._prop_dict(node_props, "tray_2_pressure"),
                "tray_pressure_drop": TopJsonToAspenExtractor._prop_dict(node_props, "tray_pressure_drop"),
                "tray_pressure": TopJsonToAspenExtractor._prop_value(node_props, "tray_pressure", []),
                "pressure_view": TopJsonToAspenExtractor._prop_dict(node_props, "pressure_view"),
                "pressure_profile": TopJsonToAspenExtractor._prop_dict(node_props, "pressure_profile"),
                "comp_spec": {
                    "SPEC_TYPE": [],
                    "SPEC_PHASE": TopJsonToAspenExtractor._restore_column_spec_phases(node_props),
                    "PEC_COMPS": TopJsonToAspenExtractor._restore_column_spec_names(node_props),
                    "PEC_COMPS_index": TopJsonToAspenExtractor._restore_column_spec_ids(node_props),
                    "SPEC_STREAMS": TopJsonToAspenExtractor._restore_column_spec_stages(node_props),
                    "SPEC_DESCRIP": TopJsonToAspenExtractor._restore_column_spec_molars(node_props),
                },
            }

        if node_type == "RecycleBreaker":
            return {"comp_nums": comp_num}

        if node_type == "ReactorConversion":
            return {"comp_nums": comp_num}

        return {"comp_nums": comp_num}

    @staticmethod
    def _restore_source_stream(node_props: Dict[str, Any], label_to_top_name: Dict[str, str]) -> Dict[str, Any]:
        compositions = {}
        row_headers = TopJsonToAspenExtractor._prop_row_header(node_props, "molar_compositions")
        values = TopJsonToAspenExtractor._prop_value(node_props, "molar_compositions", [])
        for index, header in enumerate(row_headers):
            if not TopJsonToAspenExtractor._is_real_value(header):
                header = list(label_to_top_name.keys())[index] if index < len(label_to_top_name) else header
            stream_key = next((label for label, top_name in label_to_top_name.items() if top_name == header), header)
            value = values[index] if index < len(values) else 0.0
            compositions[stream_key] = value

        return {
            "connection": {"from": None, "to": None},
            "properties": {
                "temperature": TopJsonToAspenExtractor._prop_dict(node_props, "temperature"),
                "pressure": TopJsonToAspenExtractor._prop_dict(node_props, "pressure"),
                "vapor_frac": TopJsonToAspenExtractor._prop_dict(node_props, "vapor_molar_fraction"),
                "mass_flow": TopJsonToAspenExtractor._prop_dict(node_props, "mass_flowrate"),
                "mole_flow": TopJsonToAspenExtractor._prop_dict(node_props, "molar_flowrate"),
            },
            "composition_mole_frac": compositions,
        }

    @staticmethod
    def _restore_condenser(node_props: Dict[str, Any]) -> str:
        value = str(TopJsonToAspenExtractor._prop_value(node_props, "condenser_type", "0"))
        top_vapor_fraction = TopJsonToAspenExtractor._prop_value(node_props, "top_molar_vapor_fraction")
        if value == "0":
            return "TOTAL"
        if top_vapor_fraction == 1:
            return "PARTIAL-V"
        return "PARTIAL-V-L"

    @staticmethod
    def _restore_column_spec_ids(node_props: Dict[str, Any]) -> List[Any]:
        values = []
        for key in ("comp_spec_1_id", "comp_spec_2_id"):
            value = TopJsonToAspenExtractor._prop_value(node_props, key)
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _restore_column_spec_names(node_props: Dict[str, Any]) -> List[Any]:
        values = []
        for key in ("comp_spec_1_id", "comp_spec_2_id"):
            prop = node_props.get(key, {})
            value = prop.get("realValue")
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _restore_column_spec_stages(node_props: Dict[str, Any]) -> List[Any]:
        values = []
        for key in ("comp_spec_1_stage", "comp_spec_2_stage"):
            value = TopJsonToAspenExtractor._prop_value(node_props, key)
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _restore_column_spec_phases(node_props: Dict[str, Any]) -> List[Any]:
        values = []
        for key in ("comp_spec_1_phase", "comp_spec_2_phase"):
            value = TopJsonToAspenExtractor._prop_value(node_props, key)
            if value is None:
                continue
            values.append("V" if str(value) == "0" else "L")
        return values

    @staticmethod
    def _restore_column_spec_molars(node_props: Dict[str, Any]) -> List[Any]:
        values = []
        for key in ("comp_spec_1_molar", "comp_spec_2_molar"):
            value = TopJsonToAspenExtractor._prop_value(node_props, key)
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _fill_missing_stream_compositions(streams: Dict[str, Any], component_labels: List[str]) -> None:
        empty = {label: 0.0 for label in component_labels}
        for stream in streams.values():
            composition = stream.setdefault("composition_mole_frac", {})
            for label, value in empty.items():
                composition.setdefault(label, value)

    @staticmethod
    def _empty_stream_record() -> Dict[str, Any]:
        return {
            "connection": {"from": None, "to": None},
            "properties": {
                "temperature": {"value": None, "unit": ""},
                "pressure": {"value": None, "unit": ""},
                "vapor_frac": {"value": None, "unit": ""},
                "mass_flow": {"value": None, "unit": ""},
                "mole_flow": {"value": None, "unit": ""},
            },
            "composition_mole_frac": {},
        }

    @staticmethod
    def _loads_json_array(raw: Any) -> List[Dict[str, Any]]:
        if isinstance(raw, list):
            return raw
        if not raw:
            return []
        return json.loads(raw)

    @staticmethod
    def _node_label(node: Dict[str, Any]) -> str:
        data = node.get("data") or {}
        return data.get("label") or node.get("name") or node.get("id") or ""

    @staticmethod
    def _safe_lookup(nodes: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
        for node in nodes:
            if node.get("id") == node_id:
                return node
        return None

    @staticmethod
    def _prop_dict(node_props: Dict[str, Any], key: str) -> Dict[str, Any]:
        prop = node_props.get(key) or {}
        return {
            "value": prop.get("value"),
            "unit": prop.get("unit", ""),
        }

    @staticmethod
    def _prop_value(node_props: Dict[str, Any], key: str, default: Any = None) -> Any:
        prop = node_props.get(key)
        if not isinstance(prop, dict):
            return default
        return prop.get("value", default)

    @staticmethod
    def _prop_unit(node_props: Dict[str, Any], key: str, default: str = "") -> str:
        prop = node_props.get(key)
        if not isinstance(prop, dict):
            return default
        return prop.get("unit") or default

    @staticmethod
    def _prop_rows(node_props: Dict[str, Any], key: str) -> List[Any]:
        prop = node_props.get(key) or {}
        return prop.get("rows", []) or []

    @staticmethod
    def _prop_row_header(node_props: Dict[str, Any], key: str) -> List[Any]:
        prop = node_props.get(key) or {}
        return prop.get("rowHeader", []) or []

    @staticmethod
    def _prop_cols(node_props: Dict[str, Any], key: str) -> List[Any]:
        prop = node_props.get(key) or {}
        return prop.get("cols", []) or []

    @staticmethod
    def _prop_col_header(node_props: Dict[str, Any], key: str) -> List[Any]:
        prop = node_props.get(key) or {}
        return prop.get("colHeader", []) or []

    @staticmethod
    def _is_real_value(value: Any) -> bool:
        return value is not None and str(value).strip().lower() not in {"", "null", "none"}

    @staticmethod
    def _first_real_value(*values: Any) -> Any:
        for value in values:
            if TopJsonToAspenExtractor._is_real_value(value):
                return value
        return None

    @staticmethod
    def _sort_port_maps(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        def sort_key(item: Dict[str, str]) -> Tuple[str, int]:
            port_name = next(iter(item.keys()), "")
            prefix, _, maybe_index = port_name.rpartition("_")
            if maybe_index.isdigit():
                return prefix, int(maybe_index)
            return port_name, -1

        return sorted(items, key=sort_key)
