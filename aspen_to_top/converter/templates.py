import json
import copy
from pathlib import Path
from typing import Dict, Any


class TemplateLoader:
    """ToP 模板加载器。

    Template 目录中保存了 ToP 软件期望的 JSON 片段：

    - final_template.json: 最外层项目 JSON 外壳。
    - processNodes/*.json: 各类节点外观和端口定义。
    - nodeProperties/*.json: 各类节点参数表。
    - component/*.json: 组分公有信息模板。
    - componentPrivate/*.json: 组分私有信息模板。
    - methodPrivateList/*.json: 物性方法模板。

    注意：load_template 必须返回 deep copy。因为构建多个同类型节点时，
    如果复用同一个 dict，会导致节点 ID/label/属性互相覆盖。
    """

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            current_dir = Path(__file__).parent.parent.parent
            template_dir = current_dir / "Template"
        self.template_dir = Path(template_dir)
        self._cache = {}

    def load_template(self, relative_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """加载模板并返回深拷贝。"""
        if use_cache and relative_path in self._cache:
            return copy.deepcopy(self._cache[relative_path])

        full_path = self.template_dir / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {full_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if use_cache:
            self._cache[relative_path] = data

        return copy.deepcopy(data)

    def load_node_properties(self, block_type: str) -> Dict[str, Any]:
        type_to_file = {
            "Flash2": "Flash_properties.json",
            "Heater": "Heater_properties.json",
            "Compr": "Compressor_properties.json",
            "Pump": "Pump_properties.json",
            "Valve": "Valve_properties.json",
            "Mixer": "Mixer_properties.json",
            "SSplit": "Splitter_properties.json",
            "FSplit": "Splitter_properties.json",
            "HeatX": "HeatX_properties.json",
            "RadFrac": "Column_properties.json",
            "Sep": "ComponentSplitter_properties.json",
            "RecycleBreaker": "RecycleBreaker_properties.json",
            "RStoic": "RStoic_properties.json",
        }
        filename = type_to_file.get(block_type, f"{block_type}_properties.json")
        return self.load_template(f"nodeProperties/{filename}")

    def load_process_node(self, block_type: str) -> Dict[str, Any]:
        type_to_file = {
            "Flash2": "processNodes_Flash.json",
            "Heater": "processNodes_Heater.json",
            "Compr": "processNodes_Compressor.json",
            "Pump": "processNodes_Pump.json",
            "Valve": "processNodes_Valve.json",
            "Mixer": "processNodes_Mixer.json",
            "SSplit": "processNodes_Splitter.json",
            "FSplit": "processNodes_Splitter.json",
            "HeatX": "processNodes_HeatX.json",
            "RadFrac": "processNodes_Column.json",
            "Sep": "processNodes_ComponentSplitter.json",
            "RecycleBreaker": "processNodes_RecycleBreaker.json",
            "RStoic": "processNodes_RStoic.json",
        }
        filename = type_to_file.get(block_type, f"processNodes_{block_type}.json")
        return self.load_template(f"processNodes/{filename}")

    def load_component(self, cas: str) -> Dict[str, Any]:
        return self.load_template(f"component/{cas}.json")

    def load_component_private(self, cas: str) -> Dict[str, Any]:
        return self.load_template(f"componentPrivate/{cas}.json")

    def load_method(self, method_name: str) -> Dict[str, Any]:
        return self.load_template(f"methodPrivateList/{method_name}.json")

    def load_final_template(self) -> Dict[str, Any]:
        return self.load_template("final_template.json")

    def load_component_group(self) -> Dict[str, Any]:
        return self.load_template("componentGroupPrivateList/global.json")

    def load_process_edge_template(self) -> Dict[str, Any]:
        return self.load_template("processEdges_connetion.json")
