"""命令行和流程编排入口。

这个文件不负责具体设备参数怎么读，也不负责 ToP JSON 每个字段怎么填。
它只把完整流程按三个阶段串起来：

1. _step1_extract: 通过 Aspen COM 从 .bkp 中读取标准化数据。
2. _step2_build_json: 把标准化数据构建成 ToP JSON。
3. _step3_encrypt: 调用外部加密工具把 ToP JSON 加密成 .hss。

外部业务代码推荐使用 aspen_to_top.api 中的 convert_single_bkp/convert_bkp_folder。
命令行用户则通过根目录 main.py 转发到本文件的 main()。
"""

import sys
import json
import argparse
import time
from pathlib import Path

# 项目根目录。源码运行时是仓库根目录，exe 运行时会退化为 exe 所在目录。
from aspen_to_top.utils.runtime_paths import DEFAULT_OUTPUT_DIR, TEMPLATE_DIR, WORKSPACE_ROOT

# 对外保留旧名字，避免 api.py 等调用方需要跟着改接口。
PROJECT_ROOT = WORKSPACE_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aspen_to_top.aspen.connector import AspenConnector
from aspen_to_top.aspen.extractor import AspenExtractor
from aspen_to_top.converter.json_builder import JsonBuilder
from aspen_to_top.encryption.hss_tool import HssTool
from aspen_to_top.reverse.bkp_builder import ExtractedJsonToBkpBuilder
from aspen_to_top.reverse.com_applier import ExtractedJsonComApplier
from aspen_to_top.reverse.top_json_to_aspen import TopJsonToAspenExtractor
from aspen_to_top.utils.layout import LayoutFixer, extract_coords_from_bkp


class AspenToTopConverter:
    """Aspen BKP 到 ToP HSS 一键转换器。

    这个类是内部编排器，保留较多调试能力：

    - 完整转换 BKP -> HSS。
    - 只提取 BKP 到 extracted JSON。
    - 只构建 ToP JSON。
    - 只加密 ToP JSON 到 HSS。

    对外更推荐使用 api.py 中更窄的两个函数。
    """

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = TEMPLATE_DIR
        self.template_dir = Path(template_dir)
        # 默认输出目录固定为项目根目录 output，方便外部同学使用统一约定。
        self.default_output_dir = DEFAULT_OUTPUT_DIR
        self.default_extract_json = self.default_output_dir / "aspen_fixed_data.json"

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
        """一键转换 BKP -> ToP JSON/HSS。

        参数：
            bkp_path: Aspen .bkp 文件路径。
            output_hss: HSS 输出路径；如果为空，使用 output_dir/<bkp同名>.hss。
            save_intermediate: 是否保存 Aspen 读取后的标准化 JSON。
            output_dir: 默认输出目录。
            extract_json: 标准化 JSON 输出路径，仅调试时需要指定。
            top_json: ToP JSON 输出路径，仅调试时需要指定。
            json_only: 只生成 ToP JSON，不加密 HSS。

        返回：
            包含 extract_json/top_json/hss 三个输出路径的 dict。
        """
        print("=" * 60)
        print("Aspen ToP 转换器启动")
        print("=" * 60)

        bkp_path = Path(bkp_path).resolve()
        if not bkp_path.exists():
            raise FileNotFoundError(f"BKP 文件不存在: {bkp_path}")

        bkp_name = bkp_path.stem
        output_dir_path = Path(output_dir).resolve() if output_dir else self.default_output_dir
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # 以 HSS 路径为主路径推导同名 JSON：
        # foo.hss -> foo.json -> foo.extracted.json。
        output_hss_path = Path(output_hss).resolve() if output_hss else output_dir_path / f"{bkp_name}.hss"
        output_json_path = Path(top_json).resolve() if top_json else output_hss_path.with_suffix(".json")
        extract_json_path = None
        if save_intermediate:
            extract_json_path = Path(extract_json).resolve() if extract_json else output_hss_path.with_suffix(".extracted.json")

        try:
            # Step 1 输出的是“标准化 Aspen JSON 数据结构”，不是 ToP JSON。
            step1_data = self._step1_extract(bkp_path, extract_json_path)
            print("\n" + "=" * 60)

            # Step 2 把 Aspen 数据映射到 ToP 模板字段，得到最终会被加密的 JSON。
            self._step2_build_json(step1_data, output_json_path)
            print("\n" + "=" * 60)

            if not json_only:
                # Step 3 不改 JSON 内容，只调用外部工具进行 AES/Base64 加密封装。
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
        """Step 1: 从 Aspen 提取数据。

        这里会启动 Aspen Plus COM，调用 InitFromArchive2 打开 .bkp 文件。
        读取结果由 AspenExtractor 负责，包含：

        - components: 组分信息。
        - blocks: 设备类型、端口、设备参数。
        - streams: 流股温度/压力/流量/组成。
        - methad: Aspen 物性方法。
        - processGraph: 节点、边、坐标。
        """
        print("Step 1: 从 Aspen 提取数据")
        print("-" * 40)

        connector = AspenConnector(bkp_path)
        connector.connect()

        try:
            # Aspen 的数据都挂在 COM Tree 上，Extractor 只接收 Tree，不直接关心 COM 文档对象。
            extractor = AspenExtractor(connector.get_tree(), bkp_path)
            data = extractor.extract_all()

            # processGraph 是给 ToP 图结构使用的轻量拓扑信息；
            # 这里会同时从 .bkp 原文中读取 block/stream 坐标。
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
        """构建流程图结构。

        Aspen Tree 中 Blocks 是天然设备节点；Streams 可能只是连线，也可能需要
        转换成 ToP 的 Source/Sink 节点：

        - 有来源 block 且有目标 block: stream 是一条边。
        - 没有来源 block: stream 是 Source 节点到目标 block 的边。
        - 没有目标 block: stream 是来源 block 到 Sink 节点的边。

        坐标来自 .bkp 文件中的文本片段，Source/Sink 也按流股名读取坐标。
        """
        print("构建流程图...")

        nodes = []
        edges = []
        node_lookup = {}
        
        # 1. 添加 Aspen Blocks。Block 在 ToP 中一定是设备节点。
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

        # 2. 分析 Streams，决定它在 ToP 中是边，还是 Source/Sink 节点。
        streams_root = tree.FindNode(r"\Data\Streams")
        if streams_root:
            for strm in streams_root.Elements:
                s_name = strm.Name

                # 直接从每个 Block 的 Ports 中反查当前 stream 连接到了谁。
                src_blk = None
                dst_blk = None
                
                # 遍历所有 Blocks，查找与当前流股相关的连接
                if blocks_root:
                    for block in blocks_root.Elements:
                        blk_name = block.Name
                        ports = block.FindNode("Ports")
                        if ports:
                            # F(IN) 表示该 stream 进入这个 block。
                            in_n = ports.FindNode("F(IN)")
                            if in_n:
                                for p in in_n.Elements:
                                    if p.Value == s_name:
                                        dst_blk = blk_name
                            # 下列端口表示该 stream 从这个 block 流出。
                            out_ports = [
                                "VD(OUT)", "B(OUT)", "LD(OUT)",
                                "V(OUT)", "L(OUT)", "P(OUT)",
                                "H(OUT)", "C(OUT)",
                                # RadFrac 侧线产品出口。漏掉它会把侧线产品误判成 Source。
                                "SP(OUT)",
                            ]
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

        # 3. 补坐标。extract_coords_from_bkp 会在 .bkp 原文中搜索 ID:<节点名> 后的 At x y。
        for node in nodes:
            coords = extract_coords_from_bkp(bkp_path, node["id"])
            node["x"] = coords["x"] * 100
            node["y"] = coords["y"] * -100

        return {
            "nodes": nodes,
            "edges": edges
        }

    def _step2_build_json(self, data: dict, output_json: Path):
        """Step 2: 构建 ToP JSON。

        JsonBuilder 会加载 Template 下的 ToP 模板，并填充：

        - omProject / omProcessArchive
        - omProcessGraph.processNodes/processEdges
        - componentList / componentGroup...
        - methodPrivateList
        """
        print("Step 2: 构建 ToP JSON")
        print("-" * 40)

        output_json.parent.mkdir(parents=True, exist_ok=True)
        builder = JsonBuilder(str(self.template_dir))
        builder.build(data, str(output_json))

        print("JSON 构建完成")
        print(f"输出文件: {output_json}")

    def _step3_encrypt(self, input_json: Path, output_hss: Path):
        """Step 3: 加密为 HSS。

        注意：加密算法不在本项目中实现。这里通过 HssTool 适配调用
        export-test/hss_file_tool.py，保证不修改外部工具。
        """
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
    parser = argparse.ArgumentParser(
        description="Aspen/ToP 文件转换工具，仅提供四个用户功能：单个/批量 BKP 转 HSS，单个/批量 HSS 转 BKP。"
    )
    parser.add_argument("--version", action="version", version="Aspen-ToP 1.1.0")
    subparsers = parser.add_subparsers(dest="command")

    single_bkp = subparsers.add_parser("bkp-to-hss", help="1. 单个 .bkp 文件转 .hss")
    single_bkp.add_argument("input", help="输入 .bkp 文件")
    single_bkp.add_argument("-o", "--output", help="输出 .hss 文件，默认 output/<同名>.hss")

    batch_bkp = subparsers.add_parser("batch-bkp-to-hss", help="2. 批量 .bkp 文件转 .hss")
    batch_bkp.add_argument("input_dir", help="包含 .bkp 文件的输入文件夹")
    batch_bkp.add_argument("-d", "--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出文件夹，默认 output")

    single_hss = subparsers.add_parser("hss-to-bkp", help="3. 单个 .hss 文件转 .bkp")
    single_hss.add_argument("input", help="输入 .hss 文件")
    single_hss.add_argument("-o", "--output", help="输出 .bkp 文件，默认 output/<同名>.bkp")

    batch_hss = subparsers.add_parser("batch-hss-to-bkp", help="4. 批量 .hss 文件转 .bkp")
    batch_hss.add_argument("input_dir", help="包含 .hss 文件的输入文件夹")
    batch_hss.add_argument("-d", "--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出文件夹，默认 output")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        print("\n示例:")
        print(r"   AspenToTop.exe bkp-to-hss samples\乙烯塔.bkp -o output\乙烯塔.hss")
        print(r"   AspenToTop.exe batch-bkp-to-hss samples -d output_hss")
        print(r"   AspenToTop.exe hss-to-bkp samples\乙烯塔.hss -o output\乙烯塔.bkp")
        print(r"   AspenToTop.exe batch-hss-to-bkp samples -d output_bkp")
        return

    if args.command == "bkp-to-hss":
        converter = AspenToTopConverter()
        output_dir = str(Path(args.output).resolve().parent) if args.output else str(DEFAULT_OUTPUT_DIR)
        result = converter.convert(args.input, output_hss=args.output, output_dir=output_dir)
        remove_temp_file(result.get("top_json"))
        remove_temp_file(result.get("extract_json"))
        print(f"完成: {result['hss']}")
        return

    if args.command == "batch-bkp-to-hss":
        folder = Path(args.input_dir).resolve()
        bkp_files = sorted(folder.glob("*.bkp"))
        if not bkp_files:
            parser.error(f"文件夹中没有 .bkp 文件: {folder}")
        converter = AspenToTopConverter()
        for bkp_file in bkp_files:
            result = converter.convert(str(bkp_file), output_dir=args.output_dir)
            remove_temp_file(result.get("top_json"))
            remove_temp_file(result.get("extract_json"))
            print(f"完成: {result['hss']}")
        return

    if args.command == "hss-to-bkp":
        hss_to_bkp(args.input, args.output)
        return

    if args.command == "batch-hss-to-bkp":
        folder = Path(args.input_dir).resolve()
        hss_files = sorted(folder.glob("*.hss"))
        if not hss_files:
            parser.error(f"文件夹中没有 .hss 文件: {folder}")
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        for hss_file in hss_files:
            hss_to_bkp(str(hss_file), str(output_dir / f"{hss_file.stem}.bkp"))


def hss_to_bkp(input_hss: str, output_bkp: str = None) -> str:
    hss_path = Path(input_hss).resolve()
    if not hss_path.exists():
        raise FileNotFoundError(f"HSS 文件不存在: {hss_path}")
    if hss_path.suffix.lower() != ".hss":
        raise ValueError(f"输入文件不是 .hss: {hss_path}")

    output_path = Path(output_bkp).resolve() if output_bkp else DEFAULT_OUTPUT_DIR / f"{hss_path.stem}.bkp"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    recovered_json = output_path.with_suffix(".recovered.extracted.json")

    try:
        extractor = TopJsonToAspenExtractor()
        extractor.from_hss(str(hss_path), str(recovered_json))
        builder = ExtractedJsonToBkpBuilder()
        skeleton_path = output_path.with_name(f"{output_path.stem}.skeleton{output_path.suffix}")
        builder.build_file(str(recovered_json), str(skeleton_path))
        applier = ExtractedJsonComApplier()
        result = applier.apply_file(str(recovered_json), str(skeleton_path), str(output_path))
        builder.inject_source_stream_flow_units_file(str(recovered_json), result)
        builder.inject_radfrac_mole_flow_units_file(str(recovered_json), result)
        builder.inject_radfrac_design_specs_file(str(recovered_json), result)
        remove_aspen_sidecars(output_path)
        print(f"完成: {result}")
        return result
    finally:
        for temp_file in (
            recovered_json,
            recovered_json.with_name(f"{recovered_json.stem}.decrypted.json"),
            output_path.with_name(f"{output_path.stem}.skeleton{output_path.suffix}"),
        ):
            try:
                temp_file.unlink()
            except FileNotFoundError:
                pass


def remove_aspen_sidecars(bkp_path: Path) -> None:
    for suffix in (".apw", ".def"):
        sidecar = bkp_path.with_suffix(suffix)
        for _ in range(8):
            try:
                sidecar.unlink()
                break
            except FileNotFoundError:
                break
            except PermissionError:
                time.sleep(0.5)


def remove_temp_file(path: str = None) -> None:
    if not path:
        return
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"操作失败: {exc}")
        raise SystemExit(1)
