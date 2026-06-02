import json
from pathlib import Path
import re
import textwrap
from typing import Any, Dict, List, Optional, Tuple

from ..utils.chemical_mapper import ChemicalMapper


ASPEN_HEADER_STANDARD = (
    'ASPEN "40.0" DATETIME "01/07/2026  17:18:06:99" MACHINE "WIN-X64" SITEID "" USER "Administrator"'
)
SETUP_GLOBAL = "? SETUP GLOBAL ? "
FLOWSHEET_GLOBAL = "? %M FLOWSHEET GLOBAL ?"
COMPONENTS_GLOBAL = "? COMPONENTS MAIN ? "
PROPERTIES_GLOBAL = "? %M PROPERTIES MAIN ? "
DATABANKS_GLOBAL = "? %M DATABANKS ? "


SUPPORTED_BLOCK_TYPES = {
    "Flash2",
    "Heater",
    "HeatX",
    "Valve",
    "Pump",
    "Mixer",
    "Compr",
    "FSplit",
    "RadFrac",
}


class ExtractedJsonToBkpBuilder:
    """Build a minimal Aspen BKP text archive from extracted Aspen JSON.

    Scope of this first version:
    - Source streams
    - Flash2
    - Heater
    - Valve
    - Pump
    - Mixer
    - Compr
    - Simple FSplit
    - RadFrac topology and stream attachments

    Non-goals for now:
    - Sep / RStoic / Recycle-heavy reconstruction
    - Full Aspen COM object creation from a blank document
    """

    def build_file(self, input_json: str, output_bkp: Optional[str] = None) -> str:
        input_path = Path(input_json).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Extracted JSON file not found: {input_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        content = self.render(data)
        output_path = Path(output_bkp).resolve() if output_bkp else input_path.with_suffix(".bkp")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8", newline="\n")
        return str(output_path)

    def inject_radfrac_design_specs_file(self, input_json: str, bkp_file: str) -> str:
        """Inject RadFrac design-spec statements into a COM-saved BKP archive.

        Aspen COM SaveAs may drop textual SPEC/VARY cards from the skeleton BKP.
        The extracted ToP/HSS data stores product stages, so this method maps
        stage -> product stream and writes the Aspen SPEC-STREAMS card back.
        """
        input_path = Path(input_json).resolve()
        bkp_path = Path(bkp_file).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Extracted JSON file not found: {input_path}")
        if not bkp_path.exists():
            raise FileNotFoundError(f"BKP file not found: {bkp_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        text = bkp_path.read_text(errors="ignore")
        updated = self.inject_radfrac_design_specs(data, text)
        bkp_path.write_text(updated, encoding="utf-8", newline="\n")
        return str(bkp_path)

    def inject_source_stream_flow_units_file(self, input_json: str, bkp_file: str) -> str:
        input_path = Path(input_json).resolve()
        bkp_path = Path(bkp_file).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Extracted JSON file not found: {input_path}")
        if not bkp_path.exists():
            raise FileNotFoundError(f"BKP file not found: {bkp_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        text = bkp_path.read_text(errors="ignore")
        for stream_name in self._source_stream_names(data):
            stream = data.get("streams", {}).get(stream_name, {})
            prop = stream.get("properties", {}).get("mole_flow", {})
            value, unit_code = self._mole_flow_value_and_unit_code(prop)
            text = self._replace_stream_totflow(text, stream_name, value, unit_code)
        bkp_path.write_text(text, encoding="utf-8", newline="\n")
        return str(bkp_path)

    def inject_radfrac_mole_flow_units_file(self, input_json: str, bkp_file: str) -> str:
        """Keep RadFrac molar-flow specs in the units carried by ToP/HSS.

        Aspen COM can save some RadFrac inputs using its display default
        (often kmol/sec). We rewrite the textual BKP cards so mol/s from ToP
        becomes Aspen's mol/sec instead of being interpreted as kmol/sec.
        """
        input_path = Path(input_json).resolve()
        bkp_path = Path(bkp_file).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Extracted JSON file not found: {input_path}")
        if not bkp_path.exists():
            raise FileNotFoundError(f"BKP file not found: {bkp_path}")

        with open(input_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        text = bkp_path.read_text(errors="ignore")
        for block_id, block_info in data.get("blocks", {}).items():
            if block_info.get("type") != "RadFrac":
                continue
            params = block_info.get("params", {})
            stage_count = int(float((params.get("no_trays", {}) or {}).get("value") or 2))
            outputs = self._column_outputs(block_info, params, stage_count)
            text = self._replace_radfrac_basis_d(text, block_id, params)
            for output in outputs:
                if output.get("flow") is None:
                    continue
                text = self._replace_radfrac_product_flow(text, block_id, output)

        bkp_path.write_text(text, encoding="utf-8", newline="\n")
        return str(bkp_path)

    def _replace_stream_totflow(self, bkp_text: str, stream_name: str, value: float, unit_code: str) -> str:
        stream_match = re.search(rf"\?\s+STREAM\s+MATERIAL\s+{re.escape(str(stream_name).upper())}\s+\?", bkp_text)
        if not stream_match:
            return bkp_text
        stream_start = stream_match.start()
        next_record = bkp_text.find("? ", stream_match.end())
        stream_end = next_record if next_record >= 0 else len(bkp_text)
        stream_text = bkp_text[stream_start:stream_end]
        replacement = f"TOTFLOW = {self._fmt_number(value)} {unit_code}"
        stream_text = re.sub(
            r"TOTFLOW\s*=\s*[-+0-9.Ee]+\s+<-89>\s+<\d+>",
            replacement,
            stream_text,
            count=1,
        )
        return bkp_text[:stream_start] + stream_text + bkp_text[stream_end:]

    def _replace_radfrac_basis_d(self, bkp_text: str, block_id: str, params: Dict[str, Any]) -> str:
        block_start, block_end = self._find_block_record(bkp_text, "RADFRAC", block_id)
        if block_start < 0:
            return bkp_text
        block_text = bkp_text[block_start:block_end]
        value, unit_code = self._mole_flow_value_and_unit_code(params.get("top_molar_flowrate_guess", {}))
        block_text = re.sub(
            r"BASIS-D\s*=\s*[-+0-9.Ee]+\s+<-89>\s+<\d+>",
            f"BASIS-D = {self._fmt_number(value)} {unit_code}",
            block_text,
            count=1,
        )
        return bkp_text[:block_start] + block_text + bkp_text[block_end:]

    def _replace_radfrac_product_flow(self, bkp_text: str, block_id: str, output: Dict[str, Any]) -> str:
        block_start, block_end = self._find_block_record(bkp_text, "RADFRAC", block_id)
        if block_start < 0:
            return bkp_text
        block_text = bkp_text[block_start:block_end]
        value, unit_code = self._mole_flow_value_and_unit_code({
            "value": output.get("flow"),
            "unit": output.get("flow_unit") or "mol/s",
        })
        stream_id = re.escape(str(output["stream"]))
        pattern = re.compile(
            rf"(PROD-STREAM\s*=\s*{stream_id}\b(?:(?!PROD-STREAM\s*=).)*?PROD-FLOW\s*=\s*)"
            r"[-+0-9.Ee]+\s+<-89>\s+<\d+>",
            re.DOTALL,
        )
        block_text = pattern.sub(
            lambda match: f"{match.group(1)}{self._fmt_number(value)} {unit_code}",
            block_text,
            count=1,
        )
        return bkp_text[:block_start] + block_text + bkp_text[block_end:]

    @staticmethod
    def _find_block_record(bkp_text: str, block_type: str, block_id: str) -> Tuple[int, int]:
        match = re.search(
            rf"\?\s+BLOCK\s+{re.escape(block_type)}\s+{re.escape(str(block_id))}\s+\?",
            bkp_text,
        )
        if not match:
            return -1, -1
        start = match.start()
        next_record = re.search(r"\?\s+(?:BLOCK|STREAM|REPORT|EO-CONV|EO-VARS|SETUP|FLOWSHEET)\b", bkp_text[match.end():])
        end = match.end() + next_record.start() if next_record else len(bkp_text)
        return start, end

    def inject_radfrac_design_specs(self, data: Dict[str, Any], bkp_text: str) -> str:
        result = bkp_text
        for block_id, block_info in data.get("blocks", {}).items():
            if block_info.get("type") != "RadFrac":
                continue
            params = block_info.get("params", {})
            stage_count = int(float((params.get("no_trays", {}) or {}).get("value") or 2))
            outputs = self._column_outputs(block_info, params, stage_count)
            spec_lines = self._build_radfrac_specs(params, outputs, stage_count)
            if not spec_lines:
                continue
            result = self._inject_radfrac_block_specs(result, block_id, spec_lines)
        return result

    def render(self, data: Dict[str, Any]) -> str:
        self._validate_supported_blocks(data)
        parts = [
            self._create_environment(),
            self._create_flowsheet(data),
            self._create_chemistry(data),
            self._create_properties(data),
            self._create_source_streams(data),
            self._create_blocks(data),
            self._create_control(),
        ]
        return "\n".join(part for part in parts if part).replace("  ", " ")

    def _validate_supported_blocks(self, data: Dict[str, Any]) -> None:
        unsupported = sorted(
            {
                block_info.get("type")
                for block_info in data.get("blocks", {}).values()
                if block_info.get("type") not in SUPPORTED_BLOCK_TYPES
            }
        )
        if unsupported:
            raise ValueError(
                "This minimal BKP builder only supports "
                f"{sorted(SUPPORTED_BLOCK_TYPES)}; found unsupported block types: {unsupported}"
            )

    def _create_environment(self) -> str:
        return (
            f"{ASPEN_HEADER_STANDARD}\n"
            f"{SETUP_GLOBAL}\n"
            "\\ IN-UNITS INSET = SI \\"
        )

    def _create_flowsheet(self, data: Dict[str, Any]) -> str:
        lines = [FLOWSHEET_GLOBAL]
        for block_name, block_info in data.get("blocks", {}).items():
            in_streams = [next(iter(item.values())) for item in block_info.get("in_streams", [])]
            if block_info.get("type") == "RadFrac":
                params = block_info.get("params", {})
                stage_count = int(float((params.get("no_trays", {}) or {}).get("value") or 2))
                out_streams = [item["stream"] for item in self._column_outputs(block_info, params, stage_count)]
            else:
                out_streams = [next(iter(item.values())) for item in block_info.get("out_streams", [])]
            lines.append(self._block_connect(block_name.upper(), in_streams, out_streams, block_info.get("type", "")))
        return "\n".join(lines)

    def _block_connect(self, block_id: str, in_list: List[str], out_list: List[str], unit_type: str) -> str:
        if unit_type == "Mixer":
            in_str = " ".join(f"{stream} M0-1" for stream in in_list)
            out_str = " ".join(f"{stream} M0-1" for stream in out_list)
        elif unit_type == "HeatX":
            if len(in_list) != 2 or len(out_list) != 2:
                raise ValueError(f"HeatX requires 2 inlet streams and 2 outlet streams, got {in_list} -> {out_list}")
            in_str = f"{in_list[0]} M1-2 {in_list[1]} M0-1"
            out_str = f"{out_list[1]} M0-1 {out_list[0]} M1-2"
        elif unit_type == "FSplit":
            in_str = " ".join(f"{stream} M0-1" for stream in in_list)
            out_str = " ".join(f"{stream} M0-1" for stream in out_list)
        elif unit_type == "Flash2":
            in_str = " ".join(f"{stream} M0-1" for stream in in_list)
            ports = ["M0-1", "M1-2"]
            out_str = " ".join(
                f"{stream} {ports[index] if index < len(ports) else 'M0-1'}"
                for index, stream in enumerate(out_list)
            )
        elif unit_type == "RadFrac":
            in_str = " ".join(f"{stream} M0-1" for stream in in_list)
            top = out_list[:1]
            bottom = out_list[-1:] if len(out_list) > 1 else []
            sides = out_list[1:-1]
            out_parts = [f"{stream} M0-1" for stream in top]
            out_parts.extend(f"{stream} M3-4" for stream in sides)
            out_parts.extend(f"{stream} M2-3" for stream in bottom)
            out_str = " ".join(out_parts)
        else:
            in_str = " ".join(f"{stream} M0-1" for stream in in_list)
            out_str = " ".join(f"{stream} M0-1" for stream in out_list)
        blk_type, mdl_type = self._aspen_block_type_names(unit_type)
        return (
            f'\\ BLOCK BLKID = {block_id} BLKTYPE = "{blk_type}" '
            f'MDLTYPE = "{mdl_type}" IN = ({in_str}) OUT = ({out_str}) \\ '
        )

    @staticmethod
    def _aspen_block_type_names(unit_type: str) -> Tuple[str, str]:
        names = {
            "Flash2": ("FLASH2", "Flash2"),
            "Heater": ("HEATER", "Heater"),
            "HeatX": ("HEATX", "HeatX"),
            "Valve": ("VALVE", "Valve"),
            "Pump": ("PUMP", "Pump"),
            "Mixer": ("MIXER", "Mixer"),
            "Compr": ("COMPR", "Compr"),
            "FSplit": ("FSPLIT", "FSplit"),
            "RadFrac": ("RADFRAC", "RadFrac"),
        }
        return names.get(unit_type, (unit_type.upper(), unit_type))

    def _create_chemistry(self, data: Dict[str, Any]) -> str:
        components = self._component_rows(data)
        if not components:
            raise ValueError("No components found in extracted JSON.")

        parts = []
        for index, component in enumerate(components, 1):
            suffix = " /" if index < len(components) else ""
            parts.append(f'CID = {component["cid"]} ANAME = "{component["formula"]}"{suffix}')

        component_card = "\\ COMPONENTS " + " ".join(parts) + " \\"
        return f"{COMPONENTS_GLOBAL}\n{self._wrap_bkp_cards([component_card])}"

    def _create_properties(self, data: Dict[str, Any]) -> str:
        method = (data.get("methad") or "SRK").strip() or "SRK"
        return (
            f"{PROPERTIES_GLOBAL}\n"
            f"\\ GPROPERTIES GOPSETNAME = {method} \\ \n"
            f"{DATABANKS_GLOBAL}\n"
            '\\ DATABANKS FILE-SYM-NAM = ( "APV140 PURE40" "APV140 AQUEOUS" "APV140 SOLIDS" "APV140 INORGANIC" NOASPENP ) \\'
        )

    def _create_source_streams(self, data: Dict[str, Any]) -> str:
        lines = ['? SETUP GLOBAL ? ', '\\ STREAM-CLASS SCLASS = CONVEN \\ ']
        component_rows = self._component_rows(data)
        source_stream_names = self._source_stream_names(data)

        for stream_name in source_stream_names:
            stream = data.get("streams", {}).get(stream_name, {})
            props = stream.get("properties", {})
            temp = self._convert_temperature_to_si(props.get("temperature", {}))
            pres = self._convert_pressure_to_si(props.get("pressure", {}))
            flow, flow_unit_code = self._mole_flow_value_and_unit_code(props.get("mole_flow", {}))
            compositions = stream.get("composition_mole_frac", {})

            lines.append(f'? STREAM MATERIAL {stream_name.upper()} ?')
            lines.append(
                "\\ SUBSTREAM SSID = MIXED "
                f"TEMP = {self._fmt_number(temp)} <22> <1> "
                f"PRES = {self._fmt_number(pres)} <20> <1> "
                f"FLOWBASE = MOLE TOTFLOW = {self._fmt_number(flow)} {flow_unit_code} BASIS = MOLE-FRAC \\"
            )
            lines.extend(self._build_mole_flow_lines(component_rows, compositions))

        return "\n".join(lines)

    def _create_blocks(self, data: Dict[str, Any]) -> str:
        lines: List[str] = []
        for block_name, block_info in data.get("blocks", {}).items():
            block_type = block_info.get("type")
            params = block_info.get("params", {})
            block_id = block_name.upper()

            if block_type == "Flash2":
                spec_opt = (params.get("SPEC_OPT", {}) or {}).get("value", "TP")
                pressure = self._convert_pressure_to_si(params.get("system_pressure", {}))
                if spec_opt == "PV":
                    vapor_frac = (params.get("system_vapor_molar_fraction", {}) or {}).get("value", 0)
                    lines.append(f'? BLOCK FLASH2 {block_id} ? ')
                    lines.append(
                        "\\ PARAM "
                        f"PRES = {self._fmt_number(pressure)} <20> <1> "
                        f"VFRAC = {self._fmt_fraction(vapor_frac)} <0> <0> "
                        "SPEC_OPT = PV \\"
                    )
                else:
                    temperature = self._convert_temperature_to_si(params.get("system_temperature", {}))
                    lines.append(f'? BLOCK FLASH2 {block_id} ? ')
                    lines.append(
                        "\\ PARAM "
                        f"TEMP = {self._fmt_number(temperature)} <22> <1> "
                        f"PRES = {self._fmt_number(pressure)} <20> <1> "
                        "SPEC_OPT = TP \\"
                    )
            elif block_type == "Heater":
                temperature = self._convert_temperature_to_si(params.get("outlet_stream_temperature", {}))
                pressure = self._convert_pressure_to_si(params.get("outlet_pressure", {}))
                lines.append(f'? BLOCK HEATER {block_id} ? ')
                lines.append(
                    "\\ PARAM "
                    f"TEMP = {self._fmt_number(temperature)} <22> <1> "
                    f"PRES = {self._fmt_number(pressure)} <20> <1> "
                    "DPPARMOPT = NO \\"
                )
            elif block_type == "HeatX":
                in_ids = [next(iter(item.values())) for item in block_info.get("in_streams", [])]
                out_ids = [next(iter(item.values())) for item in block_info.get("out_streams", [])]
                if len(in_ids) != 2 or len(out_ids) != 2:
                    raise ValueError(f"HeatX block {block_name} requires 2 inlet streams and 2 outlet streams")
                hot_pressure = self._convert_pressure_to_si(params.get("hot_outlet_pressure", {}))
                cold_pressure = self._convert_pressure_to_si(params.get("cold_outlet_pressure", {}))
                area = float((params.get("area", {}) or {}).get("value") or 0.0)
                u_overall = float((params.get("u_overall", {}) or {}).get("value") or 0.0)
                lines.append(f'? BLOCK HEATX {block_id} ? ')
                lines.append('; "METCBAR_MOLE" ; ; "GEN-HS" ; ')
                lines.append(
                    "\\ PARAM PROGRAM-MODE = SIMULATION "
                    f"AREA = {self._fmt_number(area)} <1> <3> "
                    f"PRES-HOT = {self._fmt_number(hot_pressure)} <20> <1> "
                    f"PRES-COLD = {self._fmt_number(cold_pressure)} <20> <1> "
                    "U-OPTION = CONSTANT SIDE-VAR = COLD \\"
                )
                lines.append(f"\\ FEEDS FHOT = {in_ids[1]} FCOLD = {in_ids[0]} \\")
                lines.append(f"\\ OUTLETS-HOT HOT-SID = {out_ids[1]} \\")
                lines.append(f"\\ OUTLETS-COLD COLD-SID = {out_ids[0]} \\")
                lines.append(f"\\ PRODUCTS PHOT = {out_ids[1]} PCOLD = {out_ids[0]} \\")
                lines.append(f'\\ "HEAT-TR-COEF" U = {self._fmt_number(u_overall)} <16> <1> \\')
            elif block_type == "Valve":
                pressure = self._convert_pressure_to_si(params.get("outlet_pressure", {}))
                lines.append(f'? BLOCK VALVE {block_id} ? ')
                lines.append(f'\\ PARAM P-OUT = {self._fmt_number(pressure)} <20> <1> \\')
            elif block_type == "Pump":
                opt_spec = (params.get("OPT_SPEC", {}) or {}).get("value", "PRES")
                pressure = self._convert_pressure_to_si(params.get("outlet_stream_pressure", {}))
                delp = self._convert_pressure_to_si(params.get("pressure_increase", {}))
                efficiency = (params.get("pumping_efficiency", {}) or {}).get("value", 1)
                lines.append(f'? BLOCK PUMP {block_id} ? ')
                if opt_spec == "DELP":
                    lines.append(
                        "\\ PARAM "
                        f"DELP = {self._fmt_number(delp)} <20> <1> "
                        f"EFF = {self._fmt_fraction(efficiency)} <0> <0> OPT-SPEC = DELP \\"
                    )
                else:
                    lines.append(
                        "\\ PARAM "
                        f"PRES = {self._fmt_number(pressure)} <20> <1> "
                        f"EFF = {self._fmt_fraction(efficiency)} <0> <0> OPT-SPEC = PRES \\"
                    )
            elif block_type == "Mixer":
                pressure = self._convert_pressure_to_si(params.get("outlet_pressure", {}))
                lines.append(f'? BLOCK MIXER {block_id} ? ')
                lines.append(f'\\ PARAM PRES = {self._fmt_number(pressure)} <20> <1> \\')
            elif block_type == "Compr":
                pressure = self._convert_pressure_to_si(params.get("outlet_stream_pressure", {}))
                seff = (params.get("isentropic_efficiency", {}) or {}).get("value", 1)
                meff = (params.get("mechanical_efficiency", {}) or {}).get("value", seff)
                lines.append(f'? BLOCK COMPR {block_id} ? ')
                lines.append(
                    "\\ PARAM TYPE = ISENTROPIC "
                    f"PRES = {self._fmt_number(pressure)} <20> <1> "
                    f"SEFF = {self._fmt_fraction(seff)} <0> <0> "
                    f"MEFF = {self._fmt_fraction(meff)} <0> <0> "
                    "SB-TOL = .00010 <0> <0> SB-MAXIT = 30 \\"
                )
            elif block_type == "FSplit":
                outlet_streams = [next(iter(item.values())) for item in block_info.get("out_streams", [])]
                ratios = self._extract_splitter_ratios(params, len(outlet_streams))
                lines.append(f'? BLOCK FSPLIT {block_id} ? ')
                lines.append(self._build_splitter_param_string(outlet_streams, ratios))
            elif block_type == "RadFrac":
                lines.extend(self._build_radfrac_block(block_id, block_info))

        return "\n".join(lines)

    def _build_radfrac_block(self, block_id: str, block_info: Dict[str, Any]) -> List[str]:
        params = block_info.get("params", {})
        stage_count = int(float((params.get("no_trays", {}) or {}).get("value") or 2))
        condenser = (params.get("CONDENSER", {}) or {}).get("value") or "TOTAL"
        feed_streams = [next(iter(item.values())) for item in block_info.get("in_streams", [])]
        feed_stages = self._normalize_numbers(params.get("feed_trays_value", []), len(feed_streams), stage_count)
        outputs = self._column_outputs(block_info, params, stage_count)

        top_pressure = self._column_pressure_value(params.get("tray_1_pressure", {}))
        second_pressure = self._column_pressure_value(params.get("tray_2_pressure", {}))
        pressure_drop = self._column_pressure_value(params.get("tray_pressure_drop", {}))
        distillate_rate, distillate_rate_unit_code = self._mole_flow_value_and_unit_code(
            params.get("top_molar_flowrate_guess", {})
        )
        reflux_ratio = float((params.get("reflux_ratio_guess", {}) or {}).get("value") or 0.0)
        top_vapor_fraction = float((params.get("top_vapor_fraction", {}) or {}).get("value") or 0.0)
        pressure_view = self._radfrac_pressure_view(params)

        lines = [f'? BLOCK RADFRAC {block_id} ? ', '; "METCBAR_MOLE" ; ; FRACT1 ; ']
        lines.append(
            "\\ PARAM "
            f"NSTAGE = {stage_count} ALGORITHM = SUM-RATES INIT-OPTION = STANDARD "
            f"VIEW-PRES = {self._quote_if_needed(pressure_view)} NSTAGEMAX = {stage_count + 1} \\"
        )
        lines.append(f'\\ "COL-CONFIG" CONDENSER = {self._quote_if_needed(condenser)} \\')
        for index, stream_id in enumerate(feed_streams):
            lines.append(
                "\\ FEEDS "
                f"FEED-SID = {stream_id} FEED-STAGE = {self._fmt_int(feed_stages[index])} \\"
            )
        lines.append(self._build_radfrac_products(outputs))
        lines.append(
            '\\ "P-SPEC2" '
            f"PRES1 = {self._fmt_number(top_pressure)} <20> <1> "
            f"PRES2 = {self._fmt_number(second_pressure)} <20> <1> \\"
        )
        lines.append(
            '\\ "COL-SPECS" '
            f"DP-STAGE = {self._fmt_number(pressure_drop)} <75> <1> "
            f"BASIS-RDV = {self._fmt_number(top_vapor_fraction)} <0> <0> "
            f"BASIS-D = {self._fmt_number(distillate_rate)} {distillate_rate_unit_code} "
            f"BASIS-RR = {self._fmt_number(reflux_ratio)} <-1> <0> \\"
        )
        lines.extend(self._build_radfrac_specs(params, outputs, stage_count))
        return lines

    def _column_outputs(
        self,
        block_info: Dict[str, Any],
        params: Dict[str, Any],
        stage_count: int,
    ) -> List[Dict[str, Any]]:
        vapor_side = self._side_draw_map(params.get("vapor_side_draw", {}), "V")
        liquid_side = self._side_draw_map(params.get("liquid_side_draw", {}), "L")
        top_outputs: List[Dict[str, Any]] = []
        vapor_side_outputs: List[Dict[str, Any]] = []
        liquid_side_outputs: List[Dict[str, Any]] = []
        bottom_outputs: List[Dict[str, Any]] = []

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
                "stage": stages[index] if index < len(stages) else 1,
                "phase": phase,
            }
            if index < len(flows) and flows[index] is not None:
                entry["flow"] = flows[index]
                entry["flow_unit"] = flow_unit[index] if isinstance(flow_unit, list) and index < len(flow_unit) else flow_unit
            result[str(stream_id)] = entry
        return result

    def _build_radfrac_products(self, outputs: List[Dict[str, Any]]) -> str:
        parts = []
        for index, output in enumerate(outputs):
            part = (
                f"PROD-STREAM = {output['stream']} "
                f"PROD-STAGE = {self._fmt_int(output['stage'])} "
                f"PROD-PHASE = {output['phase']}"
            )
            if output.get("flow") is not None:
                flow, flow_unit_code = self._mole_flow_value_and_unit_code({
                    "value": output["flow"],
                    "unit": output.get("flow_unit") or "mol/s",
                })
                part += f" PROD-FLOW = {self._fmt_number(flow)} {flow_unit_code}"
            else:
                part += " P-S = N"
            if index < len(outputs) - 1:
                part += " /"
            parts.append(part)
        return f'\\ PRODUCTS {" ".join(parts)} \\'

    def _build_radfrac_specs(
        self,
        params: Dict[str, Any],
        outputs: List[Dict[str, Any]],
        stage_count: int,
    ) -> List[str]:
        comp_spec = params.get("comp_spec", {}) or {}
        values = comp_spec.get("SPEC_DESCRIP", []) or []
        comp_names = comp_spec.get("PEC_COMPS", []) or []
        comp_indexes = comp_spec.get("PEC_COMPS_index", []) or []
        stages = comp_spec.get("SPEC_STREAMS", []) or []
        lines: List[str] = []

        for index, value in enumerate(values):
            component = self._spec_component_name(comp_names, comp_indexes, index)
            stream = self._spec_product_stream(outputs, stages[index] if index < len(stages) else None, stage_count)
            if not component or not stream:
                continue
            spec_value = self._fmt_spec_number(float(value))
            lines.append(
                "\\ SPEC "
                f'SPEC-NO = {index + 1} SPEC-TYPE = "MOLE-FRAC" '
                f"VALUE = {spec_value} <0> <0> "
                f'SPEC-COMPS = ( "{component}" ) SPEC-STREAMS = ( {stream} ) SPEC-ACTIVE = YES '
                f'SPEC-DESCRIP = "Mole purity, {spec_value}, PRODUCT" \\'
            )

        if lines:
            vary_first = self._vary_stage(outputs)
            lines.append(
                "\\ VARY VARY-NO = 1 VARTYPE = D "
                f"{'VARY-STAGE = ' + self._fmt_int(vary_first) + ' ' if vary_first is not None else ''}"
                'VARY-ACTIVE = YES VARY-DESCRIP = "Distillate rate" \\'
            )
            lines.append('\\ VARY VARY-NO = 2 VARTYPE = RR VARY-ACTIVE = YES VARY-DESCRIP = "Reflux ratio" \\')
        return lines

    def _inject_radfrac_block_specs(self, bkp_text: str, block_id: str, spec_lines: List[str]) -> str:
        block_match = re.search(rf"\?\s+BLOCK\s+RADFRAC\s+{re.escape(block_id)}\s+\?", bkp_text)
        if not block_match:
            return bkp_text
        block_start = block_match.start()

        block_end_candidates = [
            pos for pos in (
                bkp_text.find("? \"EO-CONV-OPTI\" ?", block_start),
                bkp_text.find("? REPORT", block_start),
                bkp_text.find(" GRAPHICS_BACKUP", block_start),
            )
            if pos >= 0
        ]
        block_end = min(block_end_candidates) if block_end_candidates else len(bkp_text)
        block_text = bkp_text[block_start:block_end]
        block_text = self._remove_existing_radfrac_spec_cards(block_text)

        insert_candidates = [
            block_text.find("\\ \"KLL-VECS\""),
            block_text.find("\\ \"TRSZ-VECS\""),
            block_text.find("\\ \"PCKSR-VECS\""),
        ]
        insert_candidates = [pos for pos in insert_candidates if pos >= 0]
        insert_at = min(insert_candidates) if insert_candidates else len(block_text)

        prefix = block_text[:insert_at].rstrip()
        suffix = block_text[insert_at:].lstrip()
        vector_guard = [] if "\\ \"KLL-VECS\"" in block_text else ['\\ "KLL-VECS" \\']
        # Keep each SPEC/VARY card on its own physical line. Aspen's importer is
        # sensitive to quoted strings split across lines, e.g. SPEC-DESCRIP.
        insertion = "\n" + "\n".join(spec_lines + vector_guard) + "\n"
        new_block = prefix + insertion + suffix
        return bkp_text[:block_start] + new_block + bkp_text[block_end:]

    @staticmethod
    def _wrap_bkp_cards(cards: List[str], width: int = 78) -> str:
        wrapped_cards = []
        for card in cards:
            wrapped_cards.extend(
                textwrap.wrap(
                    card,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        return "\n".join(wrapped_cards)

    @staticmethod
    def _remove_existing_radfrac_spec_cards(block_text: str) -> str:
        result = block_text
        for marker in ("\\ SPEC ", "\\ VARY "):
            while True:
                start = result.find(marker)
                if start < 0:
                    break
                next_markers = [
                    pos for pos in (
                        result.find("\\ SPEC ", start + 1),
                        result.find("\\ VARY ", start + 1),
                        result.find("\\ \"KLL-VECS\"", start + 1),
                        result.find("\\ \"TRSZ-VECS\"", start + 1),
                        result.find("\\ \"PCKSR-VECS\"", start + 1),
                    )
                    if pos >= 0
                ]
                end = min(next_markers) if next_markers else len(result)
                result = result[:start].rstrip() + " " + result[end:].lstrip()
        return result

    def _spec_component_name(self, comp_names: List[Any], comp_indexes: List[Any], index: int) -> Optional[str]:
        candidate = comp_names[index] if index < len(comp_names) else None
        if candidate:
            mapping = ChemicalMapper.get_by_aspen_name(str(candidate))
            if mapping:
                return mapping["aspen_name"]
            return str(candidate)
        if index < len(comp_indexes):
            return str(comp_indexes[index])
        return None

    @staticmethod
    def _spec_product_stream(outputs: List[Dict[str, Any]], stage: Any, stage_count: int) -> Optional[str]:
        if stage is None:
            return outputs[0]["stream"] if outputs else None
        stage_int = int(float(stage))
        for output in outputs:
            if int(float(output["stage"])) == stage_int:
                return output["stream"]
        if stage_int <= 1 and outputs:
            return outputs[0]["stream"]
        if stage_int >= stage_count and outputs:
            return outputs[-1]["stream"]
        return None

    @staticmethod
    def _vary_stage(outputs: List[Dict[str, Any]]) -> Optional[float]:
        for output in outputs[1:-1]:
            if output.get("phase") == "V":
                return output.get("stage")
        return None

    @staticmethod
    def _radfrac_pressure_view(params: Dict[str, Any]) -> str:
        """Choose the Aspen pressure page selector used by the recovered RadFrac."""
        return "TOP/BOTTOM"

    @staticmethod
    def _port_phase(port_name: str) -> str:
        return "V" if "VAPOR" in port_name.upper() else "L"

    @staticmethod
    def _normalize_numbers(values: Any, target_length: int, default: float) -> List[float]:
        normalized = list(values) if isinstance(values, list) else []
        while len(normalized) < target_length:
            normalized.append(default)
        return [float(value) for value in normalized[:target_length]]

    @staticmethod
    def _quote_if_needed(value: Any) -> str:
        text = str(value)
        if text.startswith('"') and text.endswith('"'):
            return text
        if any(char in text for char in ("-", " ")):
            return f'"{text}"'
        return text

    def _column_pressure_value(self, prop: Dict[str, Any]) -> float:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").lower()
        # Column HSS samples sometimes carry SI magnitudes with a stale "bar" unit.
        if unit == "bar":
            return value
        return self._convert_pressure_to_si(prop)

    @staticmethod
    def _raw_prop_value(prop: Dict[str, Any]) -> float:
        return float((prop or {}).get("value") or 0.0)

    def _create_control(self) -> str:
        return '? SOLVE ? \n\\ RUN-MODE MODE = SIM \\ ? REPORT STREAM-REPOR ? \n\\ OPTIONS MOLEFLOW = MOLEFLOW \\ "\\@"'

    def _component_rows(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        components = data.get("components", {})
        rows: List[Dict[str, Any]] = []
        labels = components.get("label", [])
        formulas = components.get("fenzi", [])
        aspen_names = components.get("aspen_name", [])
        cas_numbers = components.get("cas", [])

        for index, label in enumerate(labels):
            formula = formulas[index] if index < len(formulas) else None
            aspen_name = aspen_names[index] if index < len(aspen_names) else None
            cas = cas_numbers[index] if index < len(cas_numbers) else None

            if not label and aspen_name:
                mapping = ChemicalMapper.get_by_aspen_name(aspen_name)
                label = mapping["aspen_name"] if mapping else aspen_name
            if not formula and aspen_name:
                mapping = ChemicalMapper.get_by_aspen_name(aspen_name)
                formula = mapping["aspen_formula"] if mapping else aspen_name
            if (not label or not formula) and cas:
                mapping = ChemicalMapper.get_by_aspen_name(aspen_name) if aspen_name else None
                if mapping:
                    label = label or mapping["aspen_name"]
                    formula = formula or mapping["aspen_formula"]

            cid = aspen_name or label
            mapping = ChemicalMapper.get_by_aspen_name(str(cid)) if cid else None
            if mapping:
                cid = mapping["aspen_name"]
                formula = mapping["aspen_formula"]

            rows.append(
                {
                    "label": label,
                    "cid": cid,
                    "formula": formula,
                    "aspen_name": aspen_name,
                    "cas": cas,
                }
            )

        return rows

    def _source_stream_names(self, data: Dict[str, Any]) -> List[str]:
        names = []
        for stream_name, stream_info in data.get("streams", {}).items():
            connection = stream_info.get("connection", {})
            if connection.get("from") is None:
                names.append(stream_name)
        return sorted(names)

    def _build_mole_flow_lines(self, component_rows: List[Dict[str, Any]], compositions: Dict[str, Any]) -> List[str]:
        lines = []
        for component in component_rows:
            cid = component["cid"]
            flow_value = self._composition_value(compositions, component)
            lines.append(
                f'\\ MOLE-FLOW SSID1 = MIXED CID = {cid} FLOW = {self._fmt_fraction(flow_value)} <-4> <0> \\'
            )
        return lines

    @staticmethod
    def _composition_value(compositions: Dict[str, Any], component: Dict[str, Any]) -> float:
        for key in (component.get("label"), component.get("aspen_name"), component.get("cid"), component.get("formula")):
            if key in compositions:
                return float(compositions.get(key) or 0.0)
        return 0.0

    def _extract_splitter_ratios(self, params: Dict[str, Any], outlet_count: int) -> List[float]:
        values = []
        raw = params.get("split_fraction_value", [])
        if isinstance(raw, list) and raw:
            values = [float(value or 0.0) for value in raw[:outlet_count]]

        if len(values) < outlet_count:
            rows = params.get("split_fraction_rows", [])
            if rows and len(raw) >= len(rows):
                values = [float(value or 0.0) for value in raw[: len(rows)]]

        if len(values) != outlet_count:
            raise ValueError(
                f"Simple splitter requires {outlet_count} split fractions, got {len(values)}."
            )
        return values

    def _build_splitter_param_string(self, stream_ids: List[str], fractions: List[float]) -> str:
        if len(stream_ids) != len(fractions):
            raise ValueError("stream_ids and fractions must have the same length")

        parts = []
        for index, (stream_id, fraction) in enumerate(zip(stream_ids, fractions)):
            suffix = " /" if index < len(stream_ids) - 1 else ""
            parts.append(
                f"SID = {stream_id} SUBSTREAM = MIXED FRAC = {self._fmt_fraction(fraction)} <0> <0>{suffix}"
            )
        return f'\\ PARAM {" ".join(parts)} \\'

    @staticmethod
    def _convert_temperature_to_si(prop: Dict[str, Any]) -> float:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").upper()
        if "C" == unit or unit == "DEGC":
            return value + 273.15
        if "F" == unit or unit == "DEGF":
            return (value - 32.0) * 5.0 / 9.0 + 273.15
        return value

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
    def _convert_mole_flow_to_kmol_per_s(prop: Dict[str, Any]) -> float:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").lower()
        if unit == "kmol/hr":
            return value / 3600.0
        if unit == "kmol/sec" or unit == "kmol/s":
            return value
        if unit == "mol/s" or unit == "mol/sec":
            return value / 1000.0
        if unit == "mol/hr":
            return value / 1000.0 / 3600.0
        return value

    @staticmethod
    def _mole_flow_value_and_unit_code(prop: Dict[str, Any]) -> Tuple[float, str]:
        value = float((prop or {}).get("value") or 0.0)
        unit = ((prop or {}).get("unit") or "").lower()
        if unit in {"mol/s", "mol/sec"}:
            return value, "<-89> <6>"
        if unit == "mol/hr":
            return value / 3600.0, "<-89> <6>"
        if unit in {"kmol/s", "kmol/sec"}:
            return value, "<-89> <1>"
        if unit == "kmol/hr":
            return value / 3600.0, "<-89> <1>"
        return value, "<-89> <6>"

    @staticmethod
    def _fmt_number(value: float) -> str:
        text = f"{float(value):.8f}".rstrip("0").rstrip(".")
        return text if text else "0"

    @staticmethod
    def _fmt_spec_number(value: float) -> str:
        numeric = float(value)
        if numeric and abs(numeric) < 1e-4:
            mantissa, exponent = f"{numeric:.8E}".split("E")
            mantissa = mantissa.rstrip("0").rstrip(".")
            return f"{mantissa}E{exponent}"
        return ExtractedJsonToBkpBuilder._fmt_number(numeric)

    @staticmethod
    def _fmt_int(value: float) -> str:
        return str(int(float(value)))

    @staticmethod
    def _fmt_fraction(value: float) -> str:
        text = f"{float(value):.8f}".rstrip("0").rstrip(".")
        if text.startswith("0."):
            return text[1:]
        if text.startswith("-0."):
            return "-" + text[2:]
        return text if text else "0"
