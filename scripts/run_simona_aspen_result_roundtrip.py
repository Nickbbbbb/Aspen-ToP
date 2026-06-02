"""Run HSS -> BKP checks against D:\\soft\\simona_project\\aspen_result samples.

Each output sample folder intentionally contains only three user-facing files:
- source.bkp
- converted.hss
- roundtrip.bkp, or roundtrip_failed.txt when regeneration failed
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

import pythoncom
import win32com.client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aspen_to_top.api import build_bkp_from_extracted, build_bkp_from_extracted_with_com, recover_extracted_from_hss


SOURCE_ROOT = Path(r"D:\soft\simona_project\aspen_result")
OUTPUT_ROOT = PROJECT_ROOT / "simona_aspen_result_roundtrip"

SAMPLES = {
    "flash": "flash_test",
    "heater": "heater_test",
    "heatx": "heatx_test",
    "mixer": "mixer_test",
    "pump": "pump_test",
    "compressor": "comp_test",
    "splitter_fsplit": "splitter_test",
    "valve": "valve_01_20260511_173054_d38ffee8",
    "column_01": "column_01_20260511_175430_09311b39",
    "column_02": "column_02_20260511_175531_bbf70011",
    "column_03_side_draws": "column_03_20260511_175701_0169b7bb",
    "column_04_liquid_side": "column_04_20260511_175818_7bf8f448",
    "column_05": "column_05_20260511_175921_c7cdd82b",
}


def _single_file(folder: Path, suffix: str) -> Path:
    files = sorted(folder.glob(f"*{suffix}"))
    if not files:
        raise FileNotFoundError(f"No {suffix} file found in {folder}")
    return files[0]


def _block_types(extracted_json: Path) -> List[str]:
    with extracted_json.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = json.load(handle)
    return sorted({block.get("type", "") for block in data.get("blocks", {}).values()})


def _reset_output_root() -> Path:
    global OUTPUT_ROOT
    resolved = OUTPUT_ROOT.resolve()
    project = PROJECT_ROOT.resolve()
    if project not in resolved.parents:
        raise RuntimeError(f"Refusing to clean output outside project: {resolved}")
    if resolved.exists():
        try:
            shutil.rmtree(resolved)
        except PermissionError:
            OUTPUT_ROOT = PROJECT_ROOT / "simona_aspen_result_roundtrip_latest"
            resolved = OUTPUT_ROOT.resolve()
            if resolved.exists():
                shutil.rmtree(resolved, ignore_errors=True)
    resolved.mkdir(parents=True)
    (resolved / "_work").mkdir()
    return resolved


def _write_failure(path: Path, exc: BaseException) -> None:
    path.write_text(
        f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}",
        encoding="utf-8",
    )


def _keep_only(folder: Path, filenames: List[str]) -> None:
    keep = set(filenames)
    for child in folder.iterdir():
        if child.is_file() and child.name not in keep:
            try:
                child.unlink()
            except PermissionError:
                # Aspen can keep a failed archive locked after an RPC crash.
                # Leave it in place rather than aborting the whole regression run.
                pass


def _open_check_bkp(bkp_path: Path) -> None:
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.Dispatch("Apwn.Document")
        app.InitFromArchive2(str(bkp_path.resolve()))
        app.SuppressDialogs = 1
        app.Visible = False
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


def run() -> int:
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"Source sample root not found: {SOURCE_ROOT}")

    _reset_output_root()
    work_root = OUTPUT_ROOT / "_work"
    summary_rows = [
        "# Simona Aspen Result Roundtrip",
        "",
        "| sample | source dir | recovered block types | result | notes |",
        "| --- | --- | --- | --- | --- |",
    ]

    for sample_name, source_dir_name in SAMPLES.items():
        source_dir = SOURCE_ROOT / source_dir_name
        sample_out = OUTPUT_ROOT / sample_name
        sample_out.mkdir()

        result = "FAIL"
        notes = ""
        types: List[str] = []

        try:
            source_bkp = _single_file(source_dir, ".bkp")
            source_hss = _single_file(source_dir, ".hss")
            shutil.copy2(source_bkp, sample_out / "source.bkp")
            shutil.copy2(source_hss, sample_out / "converted.hss")

            recovered_json = work_root / f"{sample_name}.recovered.extracted.json"
            recover_extracted_from_hss(source_hss, recovered_json)
            types = _block_types(recovered_json)

            roundtrip_bkp = sample_out / "roundtrip.bkp"
            try:
                build_bkp_from_extracted_with_com(
                    recovered_json,
                    roundtrip_bkp,
                    run_simulation=False,
                )
                notes = "BKP generated and saved through Aspen COM"
            except Exception as com_exc:
                if sample_name != "mixer":
                    raise
                build_bkp_from_extracted(recovered_json, roundtrip_bkp)
                _open_check_bkp(roundtrip_bkp)
                notes = f"COM SaveAs failed for Mixer, fallback BKP opens in Aspen: {type(com_exc).__name__}: {com_exc}"
            _keep_only(sample_out, ["source.bkp", "converted.hss", "roundtrip.bkp"])
            result = "OK"
        except Exception as exc:
            failed_file = sample_out / "roundtrip_failed.txt"
            _write_failure(failed_file, exc)
            _keep_only(sample_out, ["source.bkp", "converted.hss", "roundtrip_failed.txt"])
            notes = f"{type(exc).__name__}: {exc}"

        summary_rows.append(
            "| {sample} | {source} | {types} | {result} | {notes} |".format(
                sample=sample_name,
                source=source_dir_name,
                types=", ".join(types) if types else "-",
                result=result,
                notes=notes.replace("|", "\\|"),
            )
        )

    shutil.rmtree(work_root, ignore_errors=True)
    (OUTPUT_ROOT / "SUMMARY.md").write_text("\n".join(summary_rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
