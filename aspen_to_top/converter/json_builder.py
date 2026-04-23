import json
from typing import Any, Dict

from .assets_builder import AssetsBuilder
from .graph_builder import GraphBuilder
from .ids import IdGenerator
from .project_builder import ProjectBuilder
from .templates import TemplateLoader


class JsonBuilder:
    """标准化 Aspen JSON -> ToP JSON 的总编排器。

    输入是 _step1_extract 得到的 extracted JSON 数据结构；
    输出是 ToP 软件能识别、并最终会被加密进 HSS 的 JSON。

    本类只做编排：

    - 生成节点/流股/项目 ID 映射。
    - 调用 ProjectBuilder 构建项目元信息。
    - 调用 GraphBuilder 构建 processNodes/processEdges。
    - 调用 AssetsBuilder 构建组分和物性方法。

    具体设备属性填充不写在这里，而是在 property_fillers.py 中注册。
    """

    def __init__(self, template_dir: str = None):
        self.template_loader = TemplateLoader(template_dir)
        self.id_generator = IdGenerator()
        self.map_of_id = {}

    def build(self, input_data: Dict[str, Any], output_json: str = "final_result.json"):
        """构建并写出 ToP JSON 文件。"""
        print("正在构建 ToP JSON...")
        # ToP 的边引用节点时用的是节点 ID，不是 Aspen 原始名称。
        # 因此构图前必须先建立 Aspen 名称 -> ToP ID 的映射。
        self._build_id_map(input_data)

        # final_template.json 是 ToP JSON 外壳，里面包含多个列表和基础字段。
        # 后续 builder 会替换其中关键段落。
        final_result = self.template_loader.load_final_template()

        project_id = self.id_generator.generate_project_id()
        process_id = self.id_generator.generate_project_id()
        component_group_id = self.id_generator.generate_secure_nineteen()

        # 三个 builder 各自负责一块 ToP JSON，避免一个巨型函数维护所有字段。
        project_builder = ProjectBuilder(self.id_generator)
        graph_builder = GraphBuilder(self.template_loader, self.map_of_id)
        assets_builder = AssetsBuilder(self.template_loader)

        final_result["omProject"] = project_builder.create_project(project_id)
        final_result["omProcessArchive"] = project_builder.create_archive(project_id, process_id)
        final_result["omProcessGraph"] = graph_builder.create_process_graph(input_data, project_id, process_id)
        final_result["componentList"] = assets_builder.create_component_list(input_data, project_id)
        final_result["componentGroupPrivateList"] = assets_builder.create_component_group_list(project_id, component_group_id)
        final_result["componentGroupDetailPrivateList"] = assets_builder.create_component_group_detail_list(input_data, component_group_id)
        final_result["methodPrivateList"] = assets_builder.create_method_list(input_data, project_id)

        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, indent=4, ensure_ascii=False)

        print(f"JSON 构建完成: {output_json}")
        return final_result

    def _build_id_map(self, input_data: Dict[str, Any]):
        """建立 Aspen 名称到 ToP ID 的映射。

        示例：

        - Aspen block FENLV -> 598fddf9_xxxxxxxx_Flash1
        - Aspen stream S1  -> 54a52706_xxxxxxxx_Source1

        后续 processEdges.source.cell/target.cell 必须引用这些 ToP ID。
        """
        self.map_of_id = {}
        self.id_generator.reset()

        for block_name, block_info in input_data["blocks"].items():
            block_type = block_info["type"]
            self.map_of_id[block_name] = self.id_generator.generate_block_id(block_name, block_type)

        for stream_name in input_data.get("streams", {}):
            stream_type = self._find_stream_node_type(input_data, stream_name)
            self.map_of_id[stream_name] = self.id_generator.generate_stream_id(stream_name, stream_type)

    @staticmethod
    def _find_stream_node_type(input_data: Dict[str, Any], stream_name: str) -> str:
        """判断某条流股在 ToP 图中是 Source 还是 Sink。

        processGraph.nodes 中只有需要显示成节点的流股：
        - 外部进料流股 -> Source
        - 外部产品流股 -> Sink
        普通设备之间的流股只作为 edge，不会创建 stream node。
        """
        for node in input_data.get("processGraph", {}).get("nodes", []):
            if stream_name == node.get("id"):
                return node.get("type", "Source")
        return "Source"
