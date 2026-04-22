import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aspen_to_top.aspen.connector import AspenConnector
from aspen_to_top.aspen.extractor import AspenExtractor
from aspen_to_top.converter.json_builder import JsonBuilder
from aspen_to_top.encryption.hss_tool import HssTool
from aspen_to_top.utils.layout import LayoutFixer, extract_coords_from_bkp


class AspenToTopConverter:
    """Aspen BKP 到 ToP HSS 一键转换器"""

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = PROJECT_ROOT / "Template"
        self.template_dir = Path(template_dir)
        self.default_output_dir = PROJECT_ROOT / "test_output"
        self.default_extract_json = PROJECT_ROOT / "aspen_fixed_data.json"

    def convert(
        self,
        bkp_path: str,
        output_hss: str = None,
        save_intermediate: bool = False,
        output_dir: str = None,
        extract_json: str = None,
        top_json: str = None,
        json_only: bool = False,
    ):
        """一键转换 BKP -> ToP JSON/HSS"""
        print("=" * 60)
        print("Aspen ToP 转换器启动")
        print("=" * 60)

        bkp_path = Path(bkp_path).resolve()
        if not bkp_path.exists():
            raise FileNotFoundError(f"BKP 文件不存在: {bkp_path}")

        bkp_name = bkp_path.stem
        output_dir_path = Path(output_dir).resolve() if output_dir else self.default_output_dir
        output_dir_path.mkdir(parents=True, exist_ok=True)

        output_hss_path = Path(output_hss).resolve() if output_hss else output_dir_path / f"{bkp_name}.hss"
        output_json_path = Path(top_json).resolve() if top_json else output_hss_path.with_suffix(".json")
        extract_json_path = None
        if save_intermediate:
            extract_json_path = Path(extract_json).resolve() if extract_json else output_hss_path.with_suffix(".extracted.json")

        try:
            step1_data = self._step1_extract(bkp_path, extract_json_path)
            print("\n" + "=" * 60)

            self._step2_build_json(step1_data, output_json_path)
            print("\n" + "=" * 60)

            if not json_only:
                self._step3_encrypt(output_json_path, output_hss_path)
                print("\n" + "=" * 60)

            print("转换完成！")
            print(f"ToP JSON: {output_json_path}")
            if extract_json_path:
                print(f"提取 JSON: {extract_json_path}")
            if not json_only:
                print(f"HSS 文件: {output_hss_path}")
            return {
                "extract_json": str(extract_json_path) if extract_json_path else None,
                "top_json": str(output_json_path),
                "hss": str(output_hss_path) if not json_only else None,
            }

        except Exception as e:
            print(f"\n转换失败: {e}")
            raise

    def _step1_extract(self, bkp_path: str, output_path: Path = None) -> dict:
        """Step 1: 从 Aspen 提取数据"""
        print("Step 1: 从 Aspen 提取数据")
        print("-" * 40)

        connector = AspenConnector(bkp_path)
        connector.connect()

        try:
            extractor = AspenExtractor(connector.get_tree(), bkp_path)
            data = extractor.extract_all()

            data["processGraph"] = self._build_process_graph(connector.get_tree(), bkp_path)

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

            print("数据提取完成")
            print(f"   - 组分数: {len(data['components'].get('cas', []))}")
            print(f"   - 模块数: {len(data['blocks'])}")
            print(f"   - 流股数: {len(data['streams'])}")
            print(f"   - 物性方法: {data.get('methad', 'N/A')}")
            if output_path:
                print(f"提取 JSON: {output_path}")

            return data
        finally:
            connector.disconnect()

    def _build_process_graph(self, tree, bkp_path: str) -> dict:
        """构建流程图结构"""
        print("构建流程图...")

        nodes = []
        edges = []
        node_lookup = {}
        
        # 1. 添加 Blocks (必定是节点)
        blocks_root = tree.FindNode(r"\Data\Blocks")
        if blocks_root:
            for block in blocks_root.Elements:
                blk_name = block.Name
                blk_type = block.AttributeValue(6)

                node = {
                    "id": blk_name,
                    "type": blk_type,
                    "data": {"label": blk_name, "aspentype": blk_type},
                    "x": 0, "y": 0
                }
                nodes.append(node)
                node_lookup[blk_name] = node

        # 2. 分析流股，决定是"边"还是"节点"
        streams_root = tree.FindNode(r"\Data\Streams")
        if streams_root:
            for strm in streams_root.Elements:
                s_name = strm.Name

                # 直接从 Block 的 Ports 中获取连接信息
                src_blk = None
                dst_blk = None
                
                # 遍历所有 Blocks，查找与当前流股相关的连接
                if blocks_root:
                    for block in blocks_root.Elements:
                        blk_name = block.Name
                        ports = block.FindNode("Ports")
                        if ports:
                            # 检查输入端口
                            in_n = ports.FindNode("F(IN)")
                            if in_n:
                                for p in in_n.Elements:
                                    if p.Value == s_name:
                                        dst_blk = blk_name
                            # 检查各种输出端口
                            out_ports = ["VD(OUT)", "B(OUT)", "LD(OUT)", "V(OUT)", "L(OUT)", "P(OUT)", "H(OUT)", "C(OUT)"]
                            for port_name in out_ports:
                                out_n = ports.FindNode(port_name)
                                if out_n:
                                    for p in out_n.Elements:
                                        if p.Value == s_name:
                                            src_blk = blk_name

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
                            "x": 0, "y": 0
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
                            "x": 0, "y": 0
                        }
                        nodes.append(node)
                        node_lookup[end_node_id] = node

                # --- 创建 Edge ---
                if start_node_id and end_node_id and start_node_id != end_node_id:
                    edges.append({
                        "source": start_node_id,
                        "target": end_node_id,
                        "label": s_name
                    })

        for node in nodes:
            coords = extract_coords_from_bkp(bkp_path, node["id"])
            node["x"] = coords["x"] * 100
            node["y"] = coords["y"] * -100

        return {
            "nodes": nodes,
            "edges": edges
        }

    def _step2_build_json(self, data: dict, output_json: Path):
        """Step 2: 构建 ToP JSON"""
        print("Step 2: 构建 ToP JSON")
        print("-" * 40)

        output_json.parent.mkdir(parents=True, exist_ok=True)
        builder = JsonBuilder(str(self.template_dir))
        builder.build(data, str(output_json))

        print("JSON 构建完成")
        print(f"输出文件: {output_json}")

    def _step3_encrypt(self, input_json: Path, output_hss: Path):
        """Step 3: 加密为 HSS"""
        print("Step 3: 加密为 HSS")
        print("-" * 40)

        output_hss.parent.mkdir(parents=True, exist_ok=True)
        HssTool.encrypt(str(input_json), str(output_hss))

    def extract_only(self, bkp_path: str, output_path: str = None):
        """仅提取数据，不转换"""
        print("数据提取模式")
        print("-" * 40)

        connector = AspenConnector(bkp_path)
        connector.connect()

        try:
            extractor = AspenExtractor(connector.get_tree(), bkp_path)
            data = extractor.extract_all()
            data["processGraph"] = self._build_process_graph(connector.get_tree(), bkp_path)

            if output_path is None:
                output_path = self.default_extract_json
            output_path = Path(output_path).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"提取完成: {output_path}")
            return str(output_path)
        finally:
            connector.disconnect()

    def build_only(self, input_json: str = None, output_json: str = None):
        """仅构建 JSON，不提取"""
        print("JSON 构建模式")
        print("-" * 40)

        if input_json is None:
            input_json = self.default_extract_json
        if output_json is None:
            output_json = self.default_output_dir / f"{Path(input_json).stem}.json"
        output_json = Path(output_json).resolve()
        output_json.parent.mkdir(parents=True, exist_ok=True)

        with open(input_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        builder = JsonBuilder(str(self.template_dir))
        builder.build(data, str(output_json))

        print(f"构建完成: {output_json}")
        return str(output_json)

    def encrypt_only(self, input_json: str = None, output_hss: str = None):
        """仅加密，不提取不构建"""
        print("加密模式")
        print("-" * 40)

        if input_json is None:
            raise ValueError("未指定输入 JSON 文件")
        if output_hss is None:
            output_hss = Path(input_json).with_suffix(".hss")
        output_hss = Path(output_hss).resolve()
        output_hss.parent.mkdir(parents=True, exist_ok=True)

        HssTool.encrypt(input_json, str(output_hss))
        print(f"加密完成: {output_hss}")
        return str(output_hss)


def main():
    parser = argparse.ArgumentParser(description="Aspen BKP to ToP HSS 转换器")
    parser.add_argument("bkp_file", nargs="*", help="BKP 文件路径，支持多个")
    parser.add_argument("-o", "--output", help="输出 HSS 文件路径；批量转换时请使用 --output-dir")
    parser.add_argument("-d", "--output-dir", help="输出目录，默认 test_output")
    parser.add_argument("-i", "--intermediate", action="store_true", help="额外保存 Aspen 提取后的标准化 JSON")
    parser.add_argument("--extract-json", help="Aspen 提取 JSON 输出路径，仅单文件转换时有效")
    parser.add_argument("--top-json", help="ToP JSON 输出路径，仅单文件转换时有效")
    parser.add_argument("--json-only", action="store_true", help="只生成 ToP JSON，不生成 HSS")
    parser.add_argument("--extract-only", metavar="JSON", help="仅提取数据到 JSON")
    parser.add_argument("--build-only", nargs="?", metavar="JSON", const="aspen_fixed_data.json", help="仅构建 JSON")
    parser.add_argument("--encrypt-only", nargs="?", metavar="JSON", const="final_result.json", help="仅加密为 HSS")
    parser.add_argument("--decrypt", nargs=2, metavar=("HSS", "JSON"), help="解密 HSS 文件")

    args = parser.parse_args()

    if args.decrypt:
        hss_file, json_file = args.decrypt
        HssTool.decrypt(hss_file, json_file)
        return

    if args.extract_only:
        converter = AspenToTopConverter()
        if not args.bkp_file:
            parser.error("--extract-only 需要提供 BKP 文件")
        converter.extract_only(args.bkp_file[0], args.extract_only)
        return

    if args.build_only:
        converter = AspenToTopConverter()
        converter.build_only(args.build_only, args.top_json)
        return

    if args.encrypt_only:
        converter = AspenToTopConverter()
        converter.encrypt_only(args.encrypt_only, args.output)
        return

    if not args.bkp_file:
        parser.print_help()
        print("\n示例:")
        print("   python main.py flash.bkp                    # 一键转换为 test_output/flash.hss")
        print("   python main.py flash.bkp -o output.hss      # 指定 HSS 输出")
        print("   python main.py flash.bkp -i                 # 同时保存提取 JSON")
        print("   python main.py flash.bkp --json-only        # 只生成 ToP JSON")
        print("   python main.py a.bkp b.bkp -d output        # 批量转换")
        print("   python main.py flash.bkp --extract-only data.json       # 仅提取")
        print("   python main.py --build-only data.json --top-json top.json # 仅构建 ToP JSON")
        print("   python main.py --encrypt-only final.json -o out.hss       # 仅加密")
        print("   python main.py --decrypt project.hss out.json  # 解密")
        return

    if len(args.bkp_file) > 1 and (args.output or args.extract_json or args.top_json):
        parser.error("批量转换不能同时使用 --output、--extract-json 或 --top-json，请使用 --output-dir")

    converter = AspenToTopConverter()
    for bkp_file in args.bkp_file:
        converter.convert(
            bkp_file,
            output_hss=args.output,
            save_intermediate=args.intermediate,
            output_dir=args.output_dir,
            extract_json=args.extract_json,
            top_json=args.top_json,
            json_only=args.json_only,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"操作失败: {exc}")
        raise SystemExit(1)
