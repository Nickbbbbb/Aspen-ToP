from typing import Any, Dict, List

from .templates import TemplateLoader
from ..utils.chemical_mapper import ChemicalMapper


class AssetsBuilder:
    """构建 ToP 工程中的组分、组分组、组分明细和物性方法列表。

    Aspen 提取层只会给出 CAS 号和物性方法名称；ToP JSON 需要的是模板化
    的对象，例如 componentPrivateList、componentGroupPrivateList 等。
    这一层负责把 Aspen 的轻量信息映射到 Template 目录中的 ToP 模板。
    """

    def __init__(self, template_loader: TemplateLoader):
        self.template_loader = template_loader

    def create_component_list(self, input_data: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        """生成 ToP 的 componentPrivateList。

        input_data["components"]["cas"] 来自 Aspen COM 读取结果。每个 CAS
        号会去 Template/component 下寻找对应模板，并通过 ChemicalMapper
        映射成 ToP 内置组分 ID。找不到模板的组分会跳过并打印警告，避免
        单个组分缺失导致整个转换中断。
        """
        result = []
        components = input_data["components"]["cas"]
        index_new = 2
        index_old = 1

        for cas in components:
            try:
                template = self.template_loader.load_component(cas)
                # ToP 使用自己的组分 ID；Aspen 的 CAS 号只作为查模板和映射的入口。
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
        """生成全局组分组。

        当前转换默认只有一个 GLOBAL 组分组，设备节点中的 component_cluster
        会指向这个组分组。
        """
        template = self.template_loader.load_component_group()
        template["projectId"] = project_id
        template["id"] = component_group_id
        return [template]

    def create_component_group_detail_list(self, input_data: Dict[str, Any], component_group_id: str) -> List[Dict[str, Any]]:
        """生成组分组和具体组分之间的关联明细。"""
        result = []
        components = input_data["components"]["cas"]
        index = 1

        for cas in components:
            try:
                template = self.template_loader.load_component_private(cas)
                template["index"] = index
                template["componentGroupId"] = component_group_id
                # componentId 必须和 create_component_list 中的组分 ID 对齐。
                template["componentId"] = ChemicalMapper.CHEMICAL_MAP.get(cas, "")
                result.append(template)
                index += 1
            except Exception as exc:
                print(f"⚠️ 加载组分详情 {cas} 失败: {exc}")

        return result

    def create_method_list(self, input_data: Dict[str, Any], project_id: str) -> List[Dict[str, Any]]:
        """生成物性方法列表。

        Aspen 读取出来的字段名目前保持为 methad，这是旧代码沿用下来的命名。
        方法模板位于 Template/methodPrivateList。若 Aspen 文件没有设置方法，
        或当前方法没有对应模板，则返回空列表。
        """
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
