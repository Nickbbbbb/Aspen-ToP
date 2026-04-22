from typing import Any, Dict, List

from .templates import TemplateLoader
from ..utils.chemical_mapper import ChemicalMapper


class AssetsBuilder:
    """Build component group, component, and property method sections."""

    def __init__(self, template_loader: TemplateLoader):
        self.template_loader = template_loader

    def create_component_list(self, input_data: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        result = []
        components = input_data["components"]["cas"]
        index_new = 2
        index_old = 1

        for cas in components:
            try:
                template = self.template_loader.load_component(cas)
                template["id"] = ChemicalMapper.CHEMICAL_MAP.get(cas, "")
                template["projectId"] = project_id
                template["indexNew"] = index_new
                template["indexOld"] = index_old
                result.append(template)
                index_new += 1
                index_old += 1
            except Exception as exc:
                print(f"⚠️ 加载组分 {cas} 失败: {exc}")

        return result

    def create_component_group_list(self, project_id: str, component_group_id: str) -> List[Dict[str, Any]]:
        template = self.template_loader.load_component_group()
        template["projectId"] = project_id
        template["id"] = component_group_id
        return [template]

    def create_component_group_detail_list(self, input_data: Dict[str, Any], component_group_id: str) -> List[Dict[str, Any]]:
        result = []
        components = input_data["components"]["cas"]
        index = 1

        for cas in components:
            try:
                template = self.template_loader.load_component_private(cas)
                template["index"] = index
                template["componentGroupId"] = component_group_id
                template["componentId"] = ChemicalMapper.CHEMICAL_MAP.get(cas, "")
                result.append(template)
                index += 1
            except Exception as exc:
                print(f"⚠️ 加载组分详情 {cas} 失败: {exc}")

        return result

    def create_method_list(self, input_data: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        method_name = input_data.get("methad", "")
        if not method_name:
            return []

        try:
            template = self.template_loader.load_method(method_name)
            template["projectId"] = project_id
            template["id"] = "2020041427883515905"
            return [template]
        except Exception as exc:
            print(f"⚠️ 加载物性方法 {method_name} 失败: {exc}")
            return []
