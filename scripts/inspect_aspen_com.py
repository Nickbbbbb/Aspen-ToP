import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pythoncom
import win32com.client


def safe_child_names(node, limit: int = 20) -> List[Optional[str]]:
    result: List[Optional[str]] = []
    if not node:
        return result
    try:
        count = min(node.Elements.Count, limit)
    except Exception:
        return result
    for index in range(1, count + 1):
        try:
            result.append(getattr(node.Elements.Item(index), "Name", None))
        except Exception:
            result.append(None)
    return result


def interesting_names(obj) -> List[str]:
    return [
        name
        for name in dir(obj)
        if not name.startswith("_")
        and any(
            key in name.lower()
            for key in ("save", "open", "archive", "init", "new", "close", "quit", "tree", "run", "engine", "find", "set", "value", "element", "attr", "delete", "remove")
        )
    ]


def descend(node, *parts: str):
    current = node
    for part in parts:
        if not current:
            return None
        try:
            current = current.FindNode(part)
        except Exception:
            return None
    return current


def inspect_document(app) -> Dict[str, Any]:
    return {"document_methods": interesting_names(app)}


def inspect_new_flowsheet(app) -> Dict[str, Any]:
    app.InitNew()
    tree = app.Tree
    data = tree.FindNode("\\Data")
    blocks = data.FindNode("Blocks") if data else None
    return {
        "tree_methods": interesting_names(tree),
        "data_children": safe_child_names(data, limit=40),
        "data_node_methods": interesting_names(data) if data else [],
        "blocks_node_methods": interesting_names(blocks) if blocks else [],
    }


def inspect_archive(app, bkp_path: Path) -> Dict[str, Any]:
    app.InitFromArchive2(str(bkp_path))
    app.SuppressDialogs = 1
    time.sleep(3)

    tree = app.Tree
    data = tree.FindNode("\\Data")
    components = descend(data, "Components")
    properties = descend(data, "Properties")
    flowsheet = descend(data, "Flowsheet")
    streams = descend(data, "Streams")
    blocks = descend(data, "Blocks")
    prop_input = descend(data, "Properties", "Specifications", "Input")

    sample_block_name = None
    sample_stream_name = None
    block_input_children: List[Optional[str]] = []
    block_ports_children: List[Optional[str]] = []
    stream_input_children: List[Optional[str]] = []

    block_names = safe_child_names(blocks, limit=20)
    stream_names = safe_child_names(streams, limit=20)
    sample_block_name = next((name for name in block_names if name), None)
    sample_stream_name = next((name for name in stream_names if name), None)

    if sample_block_name:
        block_input_children = safe_child_names(descend(blocks, sample_block_name, "Input"), limit=30)
        block_ports_children = safe_child_names(descend(blocks, sample_block_name, "Ports"), limit=30)
    if sample_stream_name:
        stream_input_children = safe_child_names(descend(streams, sample_stream_name, "Input"), limit=30)

    return {
        "archive_path": str(bkp_path),
        "data_children": safe_child_names(data, limit=20),
        "components_children": safe_child_names(components, limit=20),
        "properties_children": safe_child_names(properties, limit=20),
        "flowsheet_children": safe_child_names(flowsheet, limit=20),
        "stream_names": block_trim(stream_names),
        "block_names": block_trim(block_names),
        "property_spec_input_children": safe_child_names(prop_input, limit=30),
        "sample_block_name": sample_block_name,
        "sample_block_input_children": block_input_children,
        "sample_block_ports_children": block_ports_children,
        "sample_stream_name": sample_stream_name,
        "sample_stream_input_children": stream_input_children,
    }


def block_trim(items: List[Optional[str]]) -> List[str]:
    return [item for item in items if item]


def main():
    parser = argparse.ArgumentParser(description="Inspect Aspen Plus COM surface and common tree paths.")
    parser.add_argument("--bkp", help="Optional BKP file to inspect with InitFromArchive2.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    payload: Dict[str, Any] = {}
    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.Dispatch("Apwn.Document")
        payload["document"] = inspect_document(app)
        payload["new_flowsheet"] = inspect_new_flowsheet(app)
        try:
            app.Close()
        except Exception:
            pass
        try:
            app.Quit()
        except Exception:
            pass
        app = None
        if args.bkp:
            app = win32com.client.Dispatch("Apwn.Document")
            payload["archive"] = inspect_archive(app, Path(args.bkp).resolve())
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

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
