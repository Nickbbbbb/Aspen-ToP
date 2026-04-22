import json
from typing import Any, Dict

from .assets_builder import AssetsBuilder
from .graph_builder import GraphBuilder
from .ids import IdGenerator
from .project_builder import ProjectBuilder
from .templates import TemplateLoader


class JsonBuilder:
    """Orchestrates Aspen normalized JSON -> ToP JSON conversion."""

    def __init__(self, template_dir: str = None):
        self.template_loader = TemplateLoader(template_dir)
        self.id_generator = IdGenerator()
        self.map_of_id = {}

    def build(self, input_data: Dict[str, Any], output_json: str = "final_result.json"):
        print("正在构建 ToP JSON...")
        self._build_id_map(input_data)

        final_result = self.template_loader.load_final_template()

        project_id = self.id_generator.generate_project_id()
        process_id = self.id_generator.generate_project_id()
        component_group_id = self.id_generator.generate_secure_nineteen()

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
        for node in input_data.get("processGraph", {}).get("nodes", []):
            if stream_name == node.get("id"):
                return node.get("type", "Source")
        return "Source"
