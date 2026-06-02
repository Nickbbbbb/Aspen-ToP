import shutil
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from aspen_to_top import build_bkp_from_extracted_with_com, recover_extracted_from_hss
from aspen_to_top.main import AspenToTopConverter

EXAMPLES_DIR = WORKSPACE / "examples"
ROUNDTRIP_DIR = WORKSPACE / "roundtrip_review"
TEMP_DIR = WORKSPACE / "output" / "roundtrip_temp"


def iter_sample_bkps():
    for path in sorted(EXAMPLES_DIR.rglob("*.bkp")):
        yield path


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main():
    ROUNDTRIP_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    summary_lines = [
        "# Roundtrip Summary",
        "",
        "| Sample | BKP -> HSS | HSS -> BKP | Note |",
        "|---|---|---|---|",
    ]

    converter = AspenToTopConverter()
    for sample_bkp in iter_sample_bkps():
        sample_name = sample_bkp.stem
        sample_dir = ROUNDTRIP_DIR / sample_name
        clean_dir(sample_dir)

        source_copy = sample_dir / "source.bkp"
        shutil.copyfile(sample_bkp, source_copy)

        temp_hss = TEMP_DIR / f"{sample_name}.hss"
        temp_top_json = TEMP_DIR / f"{sample_name}.top.json"
        temp_extract_json = TEMP_DIR / f"{sample_name}.top.extracted.json"
        temp_recovered_json = TEMP_DIR / f"{sample_name}.recovered.extracted.json"

        hss_status = "FAIL"
        roundtrip_status = "FAIL"
        note = ""

        try:
            converter.convert(
                str(sample_bkp),
                output_hss=str(temp_hss),
                save_intermediate=True,
                output_dir=str(TEMP_DIR),
                extract_json=str(temp_extract_json),
                top_json=str(temp_top_json),
                json_only=False,
            )
            shutil.copyfile(temp_hss, sample_dir / "converted.hss")
            hss_status = "OK"
        except Exception as exc:
            note = f"BKP -> HSS failed: {exc}"
            write_text(sample_dir / "roundtrip_failed.txt", note)
            summary_lines.append(f"| {sample_name} | {hss_status} | {roundtrip_status} | {note} |")
            continue

        try:
            recover_extracted_from_hss(str(temp_hss), str(temp_recovered_json))
            build_bkp_from_extracted_with_com(
                str(temp_recovered_json),
                str(sample_dir / "roundtrip.bkp"),
                run_simulation=False,
            )
            roundtrip_status = "OK"
            note = "Roundtrip BKP generated successfully."
        except Exception as exc:
            note = f"HSS -> BKP failed: {exc}"
            write_text(sample_dir / "roundtrip_failed.txt", note)

        summary_lines.append(f"| {sample_name} | {hss_status} | {roundtrip_status} | {note} |")

    write_text(ROUNDTRIP_DIR / "SUMMARY.md", "\n".join(summary_lines) + "\n")
    print(f"Roundtrip review written to: {ROUNDTRIP_DIR}")


if __name__ == "__main__":
    main()
