import random
import secrets
from typing import Dict


class IdGenerator:
    """ToP JSON ID 生成器。

    ToP 节点 ID 的格式大致为：

        <类型前缀>_<随机8位hex>_<ToP节点类型名><同类计数>

    例如 Flash2 会生成类似 598fddf9_ab12cd34_Flash1。
    processEdges 中的 source.cell/target.cell 必须引用这些节点 ID，因此
    同一次构建内要由同一个 IdGenerator 维护计数和映射。
    """

    TYPE_PREFIX_MAP = {
        "Flash2": "598fddf9",
        "Mixer": "851a7777",
        "Heater": "c4cecd0c",
        "Compr": "8c7245c0",
        "SSplit": "03f69f8d",
        "FSplit": "03f69f8d",
        "Source": "54a52706",
        "Sink": "ff1924d5",
        "HeatX": "795f07b5",
        "Valve": "df08bcf0",
        "Pump": "3988f609",
        "RadFrac": "deb7b0aa",
        "Sep": "69ad4ad5",
        "RecycleBreaker": "03a1aed2",
        "RStoic": "b0bd232c",
    }

    TYPE_NAME_MAP = {
        "Flash2": "Flash",
        "Heater": "Heater",
        "Compr": "Compressor",
        "Pump": "Pump",
        "Valve": "Valve",
        "Mixer": "Mixer",
        "SSplit": "Splitter",
        "FSplit": "Splitter",
        "HeatX": "HeatExchanger",
        "RadFrac": "DistillationColumn2",
        "Sep": "ComponentSplitter",
        "RecycleBreaker": "RecycleBreaker",
        "RStoic": "ReactorConversion",
        "Source": "Source",
        "Sink": "Sink",
    }

    def __init__(self):
        # _counters 统计设备节点编号，_stream_counters 统计 Source/Sink 编号。
        self._counters = {}
        self._stream_counters = {}

    def reset(self):
        """重置计数器，保证一次新的转换从 1 开始编号。"""
        self._counters = {}
        self._stream_counters = {}

    def _generate_random_hex(self, length: int = 8) -> str:
        """生成 ToP 节点 ID 中间段使用的短随机 hex。"""
        return ''.join(random.choices('0123456789abcdef', k=length))

    def _get_counter(self, block_type: str) -> int:
        """获取某类设备的递增编号，例如 Flash1、Flash2。"""
        if block_type not in self._counters:
            self._counters[block_type] = 1
        else:
            self._counters[block_type] += 1
        return self._counters[block_type]

    def generate_block_id(self, block_name: str, block_type: str) -> str:
        """为 Aspen Block 生成 ToP 设备节点 ID。"""
        prefix = self.TYPE_PREFIX_MAP.get(block_type, "00000000")
        random_part = self._generate_random_hex(8)
        name = self.TYPE_NAME_MAP.get(block_type, block_type)
        counter = self._get_counter(block_type)
        return f"{prefix}_{random_part}_{name}{counter}"

    def generate_stream_id(self, stream_name: str, stream_type: str) -> str:
        """为 Aspen 外部流股生成 Source/Sink 节点 ID。"""
        if stream_type not in self._stream_counters:
            self._stream_counters[stream_type] = 1
        else:
            self._stream_counters[stream_type] += 1

        prefix = self.TYPE_PREFIX_MAP.get(stream_type, self._generate_random_hex(8))
        random_part = self._generate_random_hex(8)
        name = self.TYPE_NAME_MAP.get(stream_type, stream_name)
        counter = self._stream_counters[stream_type]
        return f"{prefix}_{random_part}_{name}{counter}"

    def generate_project_id(self, length: int = 8) -> str:
        """生成工程相关的短随机 ID。"""
        random_bytes = secrets.randbits(length * 4)
        return format(random_bytes, f'0{length}x')

    def generate_secure_nineteen(self, length: int = 19) -> str:
        """生成 19 位数字 ID，用于 ToP 模板中需要长数字字符串的字段。"""
        if length < 1:
            raise ValueError("长度必须大于0")
        digits = '0123456789'
        first_digit = secrets.choice('123456789')
        if length > 1:
            remaining = ''.join(secrets.choice(digits) for _ in range(length - 1))
            return first_digit + remaining
        return first_digit
