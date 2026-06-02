import json
from pathlib import Path
from typing import Any, Dict, Optional

import pythoncom
import win32com.client

from ..utils.chemical_mapper import ChemicalMapper


class ExtractedJsonComApplier:
    """Apply extracted Aspen JSON values back into a skeleton BKP via Aspen COM."""

    def apply_file(
        self,
        extracted_json: str,
        skeleton_bkp: str,
        output_bkp: Optional[str] = None,
        run_simulation: bool = False,
    ) -> str:
        input_path = Path(extracted_json).resolve()
        bkp_path = Path(skeleton_bkp).resolve()
        output_path = Path(output_bkp).resolve() if output_bkp else bkp_path

        if not input_path.exists():
            raise FileNotFoundError(f"Extracted JSON file not found: {input_path}")
        if not bkp_path.exists():
            raise FileNotFoundError(f"Skeleton BKP file not found: {bkp_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        pythoncom.CoInitialize()
        app = None
        try:
            app = win32com.client.Dispatch("Apwn.Document")
            app.InitFromArchive2(str(bkp_path))
            app.SuppressDialogs = 1
            app.Visible = False

            self._apply_source_streams(app, data)
            self._apply_blocks(app, data)

            if run_simulation:
                try:
                    app.Reinit()
                    app.Engine.Run2(1)
                except Exception:
                    pass

            if output_path == bkp_path:
                app.Save()
            else:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                app.SaveAs(str(output_path))

            return str(output_path)
        finally:
            try:
                if app:
                    app.Close()
            except Exception:
                pass
            try:
                if app:
                    app.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    def _apply_source_streams(self, app, data: Dict[str, Any]) -> None:
        component_rows = self._component_rows(data)

        for stream_name, stream_info in data.get("streams", {}).items():
            connection = stream_info.get("connection", {})
            if connection.get("from") is not None:
                continue

            props = stream_info.get("properties", {})
            self._set_value(app, fr"\Data\Streams\{stream_name}\Input\FLOWBASE", "MOLE")
            self._set_prop_value(app, fr"\Data\Streams\{stream_name}\Input\TEMP\MIXED", props.get("temperature", {}))
            self._set_prop_value(app, fr"\Data\Streams\{stream_name}\Input\PRES\MIXED", props.get("pressure", {}))
            self._set_mole_flow(app, fr"\Data\Streams\{stream_name}\Input\TOTFLOW\MIXED", props.get("mole_flow", {}))

            compositions = stream_info.get("composition_mole_frac", {})
            for component in component_rows:
                value = self._composition_value(compositions, component)
                self._set_value(app, fr"\Data\Streams\{stream_name}\Input\FLOW\MIXED\{component['cid']}", value)

    def _apply_blocks(self, app, data: Dict[str, Any]) -> None:
        for block_name, block_info in data.get("blocks", {}).items():
            block_type = block_info.get("type")
            params = block_info.get("params", {})
            base = fr"\Data\Blocks\{block_name}\Input"

            if block_type == "Flash2":
                spec_opt = (params.get("SPEC_OPT", {}) or {}).get("value")
                if spec_opt:
                    self._set_value(app, fr"{base}\SPEC_OPT", spec_opt)
                self._set_prop_value(app, fr"{base}\PRES", params.get("system_pressure", {}))
                if spec_opt == "PV":
                    self._set_prop_value(app, fr"{base}\VFRAC", params.get("system_vapor_molar_fraction", {}))
                else:
                    self._set_prop_value(app, fr"{base}\TEMP", params.get("system_temperature", {}))
                self._set_prop_value(app, fr"{base}\DUTY", params.get("system_heat_duty", {}))

            elif block_type == "Heater":
                self._set_prop_value(app, fr"{base}\TEMP", params.get("outlet_stream_temperature", {}))
                self._set_prop_value(app, fr"{base}\PRES", params.get("outlet_pressure", {}))

            elif block_type == "HeatX":
                self._set_prop_value(app, fr"{base}\PRES_HOT", params.get("hot_outlet_pressure", {}))
                self._set_prop_value(app, fr"{base}\PRES_COLD", params.get("cold_outlet_pressure", {}))
                self._set_prop_value(app, fr"{base}\AREA", params.get("area", {}))
                self._set_prop_value(app, fr"{base}\U", params.get("u_overall", {}))

            elif block_type == "Valve":
                self._set_prop_value(app, fr"{base}\P_OUT", params.get("outlet_pressure", {}))

            elif block_type == "Pump":
                opt_spec = (params.get("OPT_SPEC", {}) or {}).get("value")
                if opt_spec:
                    self._set_value(app, fr"{base}\OPT_SPEC", opt_spec)
                self._set_prop_value(app, fr"{base}\PRES", params.get("outlet_stream_pressure", {}))
                self._set_prop_value(app, fr"{base}\DELP", params.get("pressure_increase", {}))
                self._set_prop_value(app, fr"{base}\PRATIO", params.get("pressure_ratio", {}))
                self._set_prop_value(app, fr"{base}\POWER", params.get("total_power", {}))
                self._set_prop_value(app, fr"{base}\EFF", params.get("pumping_efficiency", {}))

            elif block_type == "Mixer":
                self._set_prop_value(app, fr"{base}\PRES", params.get("outlet_pressure", {}))

            elif block_type == "Compr":
                self._set_prop_value(app, fr"{base}\PRES", params.get("outlet_stream_pressure", {}))
                self._set_prop_value(app, fr"{base}\SEFF", params.get("isentropic_efficiency", {}))
                self._set_prop_value(app, fr"{base}\MEFF", params.get("mechanical_efficiency", {}))

            elif block_type == "FSplit":
                self._set_prop_value(app, fr"{base}\PRES", params.get("outlet_pressure", {}))
                ratios = params.get("split_fraction_value", []) or []
                outlet_streams = [next(iter(item.values())) for item in block_info.get("out_streams", [])]
                for index, (stream_name, ratio) in enumerate(zip(outlet_streams, ratios)):
                    target = fr"{base}\FRAC" if index == 0 else fr"{base}\FRAC\{stream_name}"
                    self._set_value(app, target, float(ratio))
                    if index == 0:
                        self._set_value(app, fr"{base}\FRAC\{stream_name}", float(ratio))

            elif block_type == "RadFrac":
                self._apply_radfrac(app, base, block_info)

    @staticmethod
    def _component_rows(data: Dict[str, Any]) -> list:
        components = data.get("components", {})
        rows = []
        labels = components.get("label", [])
        formulas = components.get("fenzi", [])
        aspen_names = components.get("aspen_name", [])

        for index, label in enumerate(labels):
            formula = formulas[index] if index < len(formulas) else None
            aspen_name = aspen_names[index] if index < len(aspen_names) else None
            cid = aspen_name or label
            mapping = ChemicalMapper.get_by_aspen_name(str(cid)) if cid else None
            if mapping:
                cid = mapping["aspen_name"]
                formula = mapping["aspen_formula"]
            rows.append({"label": label, "cid": cid, "aspen_name": aspen_name, "formula": formula})
        return rows

    @staticmethod
    def _composition_value(compositions: Dict[str, Any], component: Dict[str, Any]) -> float:
        for key in (component.get("label"), component.get("aspen_name"), component.get("cid"), component.get("formula")):
            if key in compositions:
                return float(compositions.get(key) or 0.0)
        return 0.0

    def _apply_radfrac(self, app, base: str, block_info: Dict[str, Any]) -> None:
        params = block_info.get("params", {})
        stage_count = int(float((params.get("no_trays", {}) or {}).get("value") or 2))
        self._set_value(app, fr"{base}\NSTAGE", stage_count)
        condenser = (params.get("CONDENSER", {}) or {}).get("value")
        if condenser:
            self._set_value(app, fr"{base}\CONDENSER", condenser)
        self._set_value(app, fr"{base}\VIEW_PRES", self._radfrac_pressure_view(params))
        self._set_value(app, fr"{base}\PRES1", self._column_pressure_value(params.get("tray_1_pressure", {})))
        self._set_value(app, fr"{base}\PRES2", self._column_pressure_value(params.get("tray_2_pressure", {})))
        self._set_value(app, fr"{base}\DP_STAGE", self._column_pressure_value(params.get("tray_pressure_drop", {})))
        self._set_value(app, fr"{base}\BASIS_RDV", self._raw_prop_value(params.get("top_vapor_fraction", {})))
        self._set_mole_flow(app, fr"{base}\BASIS_D", params.get("top_molar_flowrate_guess", {}))
        self._set_value(app, fr"{base}\BASIS_RR", self._raw_prop_value(params.get("reflux_ratio_guess", {})))
        self._set_value(app, fr"{base}\D_BASIS", "MOLE")
        self._set_value(app, fr"{base}\RR_BASIS", "MOLE")
        self._set_value(app, fr"{base}\RDV_BASIS", "MOLE")

        feed_streams = [next(iter(item.values())) for item in block_info.get("in_streams", [])]
        feed_stages = self._normalize_numbers(params.get("feed_trays_value", []), len(feed_streams), stage_count)
        for index, (stream_id, stage) in enumerate(zip(feed_streams, feed_stages)):
            target = fr"{base}\FEED_STAGE" if index == 0 else fr"{base}\FEED_STAGE\{stream_id}"
            self._set_value(app, target, int(stage))
            self._set_value(app, fr"{base}\FEED_STAGE\{stream_id}", int(stage))

        for index, output in enumerate(self._column_outputs(block_info, params, stage_count)):
            stream_id = output["stream"]
            stage_target = fr"{base}\PROD_STAGE" if index == 0 else fr"{base}\PROD_STAGE\{stream_id}"
            phase_target = fr"{base}\PROD_PHASE" if index == 0 else fr"{base}\PROD_PHASE\{stream_id}"
            self._set_value(app, stage_target, int(output["stage"]))
            self._set_value(app, phase_target, output["phase"])
            self._set_value(app, fr"{base}\PROD_STAGE\{stream_id}", int(output["stage"]))
            self._set_value(app, fr"{base}\PROD_PHASE\{stream_id}", output["phase"])
            if output.get("flow") is not None:
                self._set_mole_flow(app, fr"{base}\PROD_FLOW\{stream_id}", {
                    "value": output["flow"],
                    "unit": output.get("flow_unit") or "mol/s",
                })

    def _column_outputs(
        self,
        block_info: Dict[str, Any],
        params: Dict[str, Any],
        stage_count: int,
    ) -> list:
        vapor_side = self._side_draw_map(params.get("vapor_side_draw", {}), "V")
        liquid_side = self._side_draw_map(params.get("liquid_side_draw", {}), "L")
        top_outputs = []
        vapor_side_outputs = []
        liquid_side_outputs = []
        bottom_outputs = []

        for item in block_info.get("out_streams", []):
            port_name, stream_id = next(iter(item.items()))
            port_upper = port_name.upper()
            if "TOP" in port_upper:
                top_outputs.append({"stream": stream_id, "stage": 1, "phase": self._port_phase(port_name)})
            elif "BOTTOM" in port_upper:
                bottom_outputs.append({"stream": stream_id, "stage": stage_count, "phase": self._port_phase(port_name)})
            elif stream_id in vapor_side:
                vapor_side_outputs.append({"stream": stream_id, **vapor_side[stream_id]})
            elif stream_id in liquid_side:
                liquid_side_outputs.append({"stream": stream_id, **liquid_side[stream_id]})
            else:
                liquid_side_outputs.append({"stream": stream_id, "stage": stage_count, "phase": self._port_phase(port_name)})

        return top_outputs + vapor_side_outputs + liquid_side_outputs + bottom_outputs

    @staticmethod
    def _side_draw_map(draw_info: Dict[str, Any], phase: str) -> Dict[str, Dict[str, Any]]:
        names = draw_info.get("stream_name", []) or []
        stages = draw_info.get("stages", []) or []
        flows = draw_info.get("flow", []) or []
        flow_unit = draw_info.get("flow_unit") or "mol/s"
        result = {}
        for index, stream_id in enumerate(names):
            if not stream_id:
                continue
            entry = {
                "stage": int(float(stages[index])) if index < len(stages) else 1,
                "phase": phase,
            }
            if index < len(flows) and flows[index] is not None:
                entry["flow"] = flows[index]
                entry["flow_unit"] = flow_unit[index] if isinstance(flow_unit, list) and index < len(flow_unit) else flow_unit
            result[str(stream_id)] = entry
        return result

    @staticmethod
    def _port_phase(port_name: str) -> str:
        return "V" if "VAPOR" in port_name.upper() else "L"

    @staticmethod
    def _normalize_numbers(values: Any, target_length: int, default: float) -> list:
        normalized = list(values) if isinstance(values, list) else []
        while len(normalized) < target_length:
            normalized.append(default)
        return [float(value) for value in normalized[:target_length]]

    @staticmethod
    def _radfrac_pressure_view(params: Dict[str, Any]) -> str:
        return "TOP/BOTTOM"

    def _column_pressure_value(self, prop: Dict[str, Any]) -> float:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").lower()
        if unit == "bar":
            return value
        return self._convert_pressure_to_si(prop)

    @staticmethod
    def _raw_prop_value(prop: Dict[str, Any]) -> float:
        return float((prop or {}).get("value") or 0.0)

    def _set_prop_value(self, app, path: str, prop: Dict[str, Any]) -> bool:
        if not prop:
            return False
        value = prop.get("value")
        unit = prop.get("unit", "")
        if value is None:
            return False
        if unit:
            if self._set_value_and_unit(app, path, value, unit):
                return True
        return self._set_value(app, path, value)

    def _set_mole_flow(self, app, path: str, prop: Dict[str, Any]) -> bool:
        if not prop:
            return False
        value = prop.get("value")
        unit = (prop.get("unit") or "").lower()
        if value is None:
            return False

        numeric = float(value)
        if unit == "kmol/hr":
            numeric = numeric / 3600.0
            unit = "kmol/sec"
        elif unit in {"mol/s", "mol/sec"}:
            unit = "mol/sec"
        elif unit == "mol/hr":
            numeric = numeric / 3600.0
            unit = "mol/sec"
        elif unit in {"kmol/sec", "kmol/s"}:
            unit = "kmol/sec"

        if unit:
            if self._set_value_and_unit(app, path, numeric, unit):
                return True
        return self._set_value(app, path, numeric)

    @staticmethod
    def _convert_pressure_to_si(prop: Dict[str, Any]) -> float:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").lower()
        if unit in {"pa", "n/sqm", "n/m2"}:
            return value
        if unit == "bar":
            return value * 1e5
        if unit == "atm":
            return value * 101325
        if unit == "kpa":
            return value * 1e3
        if unit == "mpa":
            return value * 1e6
        if unit == "psi":
            return value * 6894.76
        return value

    @staticmethod
    def _set_value(app, path: str, value: Any) -> bool:
        try:
            node = app.Tree.FindNode(path)
            if not node:
                return False
            node.Value = value
            return True
        except Exception:
            return False

    @staticmethod
    def _set_value_and_unit(app, path: str, value: Any, unit: str) -> bool:
        try:
            node = app.Tree.FindNode(path)
            if not node:
                return False
            node.SetValueAndUnit(value, unit)
            return True
        except Exception:
            return False
