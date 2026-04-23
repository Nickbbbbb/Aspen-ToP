from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseBlockExtractor(ABC):
    """设备参数提取器基类。

    每个 Aspen 模块类型对应一个独立 extractor，例如 FlashExtractor、
    PumpExtractor、ColumnExtractor。这样新增设备时只需要新增一个文件并
    在 extractor.py 的 BLOCK_EXTRACTORS 中注册，避免把所有设备参数读取
    都塞进一个巨大的 if-else。
    """

    @staticmethod
    @abstractmethod
    def extract(tree, block_name: str, comp_count: int, outputs: List[Dict], block_type: str = "") -> Dict[str, Any]:
        """从 Aspen Tree 中读取某个设备的参数。

        tree 是 Aspen COM 暴露的 Tree 对象；block_name 是 Aspen flowsheet
        中的模块名；comp_count 是全局组分数；outputs 是端口解析阶段得到
        的出口端口信息，精馏塔等设备会用它判断产品相态。
        """
        pass

    @staticmethod
    def get_prop(tree, path: str, default_unit: str = "") -> Dict[str, Any]:
        """安全读取 Aspen Tree 节点的值和单位。

        Aspen COM 节点可能不存在，也可能 Value 为 None。这里统一返回
        {"value": ..., "unit": ...}，让后续 JSON 构建层不用直接处理 COM
        异常和空节点。
        """
        try:
            node = tree.FindNode(path)
            if node:
                unit = getattr(node, "UnitString", default_unit)
                val = node.Value
                if val is None:
                    val = 0.0
                return {"value": val, "unit": unit}
            return {"value": None, "unit": default_unit}
        except Exception:
            return {"value": None, "unit": default_unit}
