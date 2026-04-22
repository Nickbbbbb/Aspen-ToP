# Aspen-ToP 开发需求文档

## 目标

本项目的目标是把 Aspen Plus `.bkp` 文件转换为 ToP 可导入编辑的 `.hss` 文件。

核心链路：

```text
BKP 文件
  -> Aspen COM 读取
  -> 标准化 Aspen JSON
  -> ToP JSON
  -> export-test/hss_file_tool.py 加密
  -> HSS 文件
```

## 分层职责

### 入口层

文件：

- `main.py`
- `aspen_to_top/main.py`
- `aspen_to_top/api.py`

职责：

- 处理 CLI/API 参数。
- 编排完整流程。
- 决定输出路径。
- 不直接写具体设备参数解析逻辑。

常用命令：

```bash
python main.py case.bkp -o output\case.hss -i
```

输出：

- `output\case.hss`: ToP 导入文件
- `output\case.json`: 最终 ToP JSON
- `output\case.extracted.json`: Aspen COM 提取后的标准化 JSON

### Aspen 读取层

文件：

- `aspen_to_top/aspen/connector.py`
- `aspen_to_top/aspen/extractor.py`
- `aspen_to_top/aspen/ports.py`
- `aspen_to_top/aspen/blocks/*.py`

职责：

- 只负责从 Aspen COM Tree 中读取信息。
- 输出标准化 Aspen JSON，不关心 ToP 模板细节。
- 各设备的参数读取放在 `aspen_to_top/aspen/blocks/` 下。
- 各设备的端口读取和 ToP 端口名映射放在 `aspen_to_top/aspen/ports.py` 下。

标准化输出结构：

```json
{
  "components": {},
  "blocks": {},
  "streams": {},
  "methad": "",
  "processGraph": {
    "nodes": [],
    "edges": []
  }
}
```

约束：

- COM 路径访问尽量集中在对应设备 extractor 中。
- 不在 extractor 里生成 ToP 的 `nodeProperties`。
- 坐标从 `.bkp` 中读取，Source/Sink 也要按流股名读取坐标。
- `AspenExtractor` 只负责调度，不继续增加端口类型 `if/elif`。

端口解析规则：

- 默认设备使用 `parse_default_ports()`。
- 特殊设备在 `PORT_PARSERS` 注册表中注册解析函数。
- 端口解析函数只返回标准化的 `in_streams/out_streams`，并登记拓扑。
- 设备参数 extractor 可以读取 `outputs`，但不应重新实现通用端口映射。

### ToP 构建层

文件：

- `aspen_to_top/converter/json_builder.py`
- `aspen_to_top/converter/project_builder.py`
- `aspen_to_top/converter/graph_builder.py`
- `aspen_to_top/converter/assets_builder.py`
- `aspen_to_top/converter/templates.py`
- `aspen_to_top/converter/ids.py`
- `aspen_to_top/converter/property_fillers.py`

职责：

- 把标准化 Aspen JSON 转成 ToP JSON。
- 根据模板生成 `processNodes`、`processEdges`、组分、物性方法等字段。
- 设备属性差异由 `property_fillers.py` 的注册表处理。

文件职责：

- `json_builder.py`: 总编排，只负责调用各子 builder 并写出 JSON。
- `project_builder.py`: 构建 `omProject` 和 `omProcessArchive`。
- `graph_builder.py`: 构建 `omProcessGraph`、`processNodes`、`processEdges`、Source/Sink 属性。
- `assets_builder.py`: 构建 `componentList`、组分组、组分详情、物性方法。
- `property_fillers.py`: 按设备类型填充 block 节点的 `nodeProperties`。
- `templates.py`: 加载模板，必须返回深拷贝。
- `ids.py`: 生成 ToP 节点、流股、项目相关 ID。

约束：

- `JsonBuilder` 只做流程编排，不写设备类型的大段 `if/elif`。
- 图结构变化优先改 `graph_builder.py`。
- 项目元信息变化优先改 `project_builder.py`。
- 组分和物性方法变化优先改 `assets_builder.py`。
- 模板加载必须返回深拷贝，避免多个节点共用同一个 dict。
- `processEdges.source.cell` 和 `processEdges.target.cell` 必须能在 `processNodes.id` 中找到。

### HSS 加密层

文件：

- `aspen_to_top/encryption/hss_tool.py`
- `export-test/hss_file_tool.py`

职责：

- `export-test/hss_file_tool.py` 是外部工具，不修改。
- `aspen_to_top/encryption/hss_tool.py` 只做适配调用。

## 新增设备类型流程

以新增 Aspen 设备类型 `NewBlock` 为例：

1. 新增 Aspen 参数提取器

在 `aspen_to_top/aspen/blocks/new_block.py` 中实现：

```python
from .base import BaseBlockExtractor


class NewBlockExtractor(BaseBlockExtractor):
    @staticmethod
    def extract(tree, block_name, comp_count, outputs):
        return {
            "comp_nums": comp_count
        }
```

2. 注册 Aspen block 类型

在 `aspen_to_top/aspen/extractor.py` 的 `BLOCK_EXTRACTORS` 中注册：

```python
"NewBlock": NewBlockExtractor,
```

3. 添加端口解析规则

如果新设备符合默认端口规则，不需要改动。

如果新设备有特殊端口，在 `aspen_to_top/aspen/ports.py` 中新增：

```python
def parse_new_block_ports(tree, block_name, block_type, ports, register_topology):
    inputs = []
    outputs = []
    add_indexed_inputs(inputs, ports, "F(IN)", "inlet_{}", block_name, register_topology)
    add_outputs(outputs, ports, "P(OUT)", "outlet_0", block_name, register_topology)
    return inputs, outputs
```

并注册：

```python
PORT_PARSERS["NewBlock"] = parse_new_block_ports
```

4. 添加 ToP 模板映射

在 `aspen_to_top/converter/templates.py` 中补充：

- `load_node_properties()` 的 Aspen 类型到 `nodeProperties` 模板文件映射。
- `load_process_node()` 的 Aspen 类型到 `processNodes` 模板文件映射。

5. 添加 ID 类型映射

在 `aspen_to_top/converter/ids.py` 中补充：

- `TYPE_PREFIX_MAP`
- `TYPE_NAME_MAP`

6. 添加属性填充器

在 `aspen_to_top/converter/property_fillers.py` 中新增：

```python
def fill_new_block(node_props, params):
    node_props["comp_num"]["value"] = params.get("comp_nums", 0)
    return node_props
```

并注册：

```python
PROPERTY_FILLERS["NewBlock"] = fill_new_block
```

7. 准备模板文件

确保以下模板存在：

- `Template/processNodes/processNodes_NewBlock.json`
- `Template/nodeProperties/NewBlock_properties.json`

8. 验证

至少运行：

```bash
python -m compileall aspen_to_top main.py
python main.py sample.bkp -o output\sample.hss -i
```

检查：

- `output\sample.extracted.json` 中 block 参数是否正确。
- `output\sample.json` 中 `processNodes` 是否存在新节点。
- 每条 edge 的 source/target 是否能找到节点 id。
- ToP 软件能否导入 `.hss`。

## 开发规范

- 不修改 `export-test/hss_file_tool.py`。
- 不把 COM 读取逻辑写进 ToP 构建层。
- 不把 ToP 模板字段写进 Aspen 提取层。
- 新设备优先新增独立文件和注册表，不继续扩大单个函数。
- 对模板 dict 的修改必须发生在深拷贝对象上。
- 输出 HSS 时必须同时保留最终 ToP JSON，便于定位导入失败原因。

## 当前已知风险

- Aspen COM 只能在安装 Aspen Plus 且 COM 可用的 Windows 环境中完整验证。
- `processEdges` 的顺序不应该作为业务含义依赖；业务含义由 label、source、target、port 决定。
- 部分设备端口规则仍集中在 `AspenExtractor._extract_block_ports()`，后续建议继续拆成端口解析注册表。

## 下一步建议

1. 给 `output\case.json` 这种 ToP JSON 增加结构校验脚本。
2. 给典型设备准备最小 `.extracted.json` 样例，减少对 Aspen COM 的测试依赖。
3. 把 `extract_components()`、`extract_streams()` 继续拆成 `components.py`、`streams.py`，让 `AspenExtractor` 只保留编排逻辑。
