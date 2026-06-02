"""Export Aspen block input variables through Aspen COM.

This is a small inspection helper for blocks with very large Input trees, such
as RadFrac. It does not modify the Aspen file.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Iterable

import pythoncom
import win32com.client


DEFAULT_KEYWORDS = (
    "SPEC",
    "VARY",
    "VAR",
    "DESIGN",
    "PRES",
    "PRESS",
    "STAGE",
    "PRODUCT",
    "PROD",
)


def _safe_value(node: Any) -> Any:
    try:
        return node.Value
    except Exception:
        return ""


def _safe_unit(node: Any) -> str:
    try:
        return node.UnitString
    except Exception:
        return ""


def _safe_name(node: Any) -> str:
    try:
        return str(node.Name)
    except Exception:
        return ""


def _children(node: Any) -> Iterable[Any]:
    try:
        elements = node.Elements
        count = elements.Count
    except Exception:
        return []

    result = []
    for index in range(1, count + 1):
        try:
            child = elements.Item(index)
        except Exception:
            child = None
        if child is not None:
            result.append(child)
    return result


def _matches(name: str, keywords: tuple[str, ...]) -> bool:
    upper = name.upper()
    return any(keyword in upper for keyword in keywords)


def _collect_input_rows(app: Any, block_id: str, keywords: tuple[str, ...], include_all: bool) -> list[dict[str, Any]]:
    base = fr"\Data\Blocks\{block_id}\Input"
    input_node = app.Tree.FindNode(base)
    rows: list[dict[str, Any]] = []
    if not input_node:
        return rows

    for node in _children(input_node):
        name = _safe_name(node)
        if not include_all and not _matches(name, keywords):
            continue
        rows.append(
            {
                "path": fr"{base}\{name}",
                "name": name,
                "row": "",
                "value": _safe_value(node),
                "unit": _safe_unit(node),
            }
        )
        for child in _children(node):
            rows.append(
                {
                    "path": fr"{base}\{name}\{_safe_name(child)}",
                    "name": name,
                    "row": _safe_name(child),
                    "value": _safe_value(child),
                    "unit": _safe_unit(child),
                }
            )
    return rows


def _collect_subobject_rows(app: Any, block_id: str) -> list[dict[str, Any]]:
    base = fr"\Data\Blocks\{block_id}\Subobjects"
    subobjects = app.Tree.FindNode(base)
    rows: list[dict[str, Any]] = []
    if not subobjects:
        return rows

    for node in _children(subobjects):
        rows.append(
            {
                "path": fr"{base}\{_safe_name(node)}",
                "name": _safe_name(node),
                "row": "",
                "value": _safe_value(node),
                "unit": _safe_unit(node),
            }
        )
        for child in _children(node):
            rows.append(
                {
                    "path": fr"{base}\{_safe_name(node)}\{_safe_name(child)}",
                    "name": _safe_name(node),
                    "row": _safe_name(child),
                    "value": _safe_value(child),
                    "unit": _safe_unit(child),
                }
            )
    return rows


def export_variables(
    bkp_path: Path,
    output_csv: Path,
    block_id: str = "B1",
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
    include_all: bool = False,
) -> None:
    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("Apwn.Document")
    try:
        app.InitFromArchive2(str(bkp_path.resolve()))
        rows = _collect_input_rows(app, block_id, keywords, include_all)
        rows.extend(_collect_subobject_rows(app, block_id))
    finally:
        try:
            app.Close(False)
        except Exception:
            pass
        pythoncom.CoUninitialize()

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "name", "row", "value", "unit"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Aspen block variables to CSV.")
    parser.add_argument("bkp", type=Path, help="Aspen .bkp file")
    parser.add_argument("--block", default="B1", help="Block ID, default: B1")
    parser.add_argument("--output", type=Path, default=Path("output/aspen_block_variables.csv"))
    parser.add_argument("--all", action="store_true", help="Export all Input nodes, not only useful keywords")
    parser.add_argument(
        "--keywords",
        default=",".join(DEFAULT_KEYWORDS),
        help="Comma separated Input node name filters",
    )
    args = parser.parse_args()

    keywords = tuple(item.strip().upper() for item in args.keywords.split(",") if item.strip())
    export_variables(args.bkp, args.output, args.block, keywords, args.all)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
