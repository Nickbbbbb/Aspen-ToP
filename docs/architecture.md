# Aspen-ToP 项目总览

## 项目目标

Aspen-ToP 的目标是把 Aspen Plus `.bkp` 文件转换为 ToP 软件可导入编辑的 `.hss` 文件。

转换链路：

```text
Aspen .bkp
  -> Aspen COM 读取
  -> 标准化 extracted JSON
  -> ToP JSON
  -> export-test 加密工具
  -> ToP .hss
```

生成 HSS 时会保留最终 ToP JSON，便于排查 ToP 导入失败问题。

## 当前主入口

推荐入口：

```text
main.py
aspen_to_top/main.py
aspen_to_top/api.py
```

`main.py` 是根目录 CLI 包装入口，实际逻辑在 `aspen_to_top/main.py`。

## 核心目录

### aspen_to_top

项目主包，当前新代码都应放在这里。

```text
aspen_to_top/
  main.py                  CLI 编排
  api.py                   Python API
  aspen/                   Aspen COM 读取层
  converter/               ToP JSON 构建层
  encryption/              HSS 加密适配层
  utils/                   坐标、组分名映射等工具
```

### Template

ToP JSON 模板目录，运行时必需。

```text
Template/
  final_template.json
  processEdges_connetion.json
  processNodes/
  nodeProperties/
  component/
  componentPrivate/
  componentGroupPrivateList/
  methodPrivateList/
```

### export-test

外部 HSS 加密工具目录。

当前项目通过 `aspen_to_top/encryption/hss_tool.py` 适配调用：

```text
export-test/hss_file_tool.py
```

约束：不要直接修改 `export-test/hss_file_tool.py`。

### docs

开发、使用、清理说明文档。

## Aspen 读取层

目录：

```text
aspen_to_top/aspen/
```

职责：

- 打开 Aspen COM。
- 从 Aspen Tree 读取组分、物性方法、流股、设备参数、端口拓扑。
- 输出标准化 extracted JSON。
- 不生成 ToP 模板字段。

关键文件：

- `connector.py`: 打开和关闭 Aspen Plus COM。
- `extractor.py`: 读取总编排。
- `ports.py`: Aspen 端口到 ToP 端口名的映射规则。
- `blocks/*.py`: 各设备参数读取器。

设备参数读取已按设备拆分，例如：

```text
blocks/flash.py
blocks/pump.py
blocks/column.py
blocks/heatx.py
```

端口规则在 `ports.py` 中通过注册表维护：

```python
PORT_PARSERS = {
    "Mixer": parse_mixer_ports,
    "RadFrac": parse_column_ports,
    "SSplit": parse_multi_product_ports,
    "FSplit": parse_multi_product_ports,
    "Sep": parse_multi_product_ports,
}
```

## ToP JSON 构建层

目录：

```text
aspen_to_top/converter/
```

职责：

- 把 extracted JSON 转成 ToP JSON。
- 生成 `omProject`、`omProcessArchive`、`omProcessGraph`。
- 生成 `processNodes`、`processEdges`。
- 生成组分、组分组、物性方法。

关键文件：

- `json_builder.py`: 总编排器，只负责调用各子 builder。
- `project_builder.py`: 构建项目元信息。
- `graph_builder.py`: 构建节点、边、Source/Sink 属性。
- `assets_builder.py`: 构建组分和物性方法。
- `property_fillers.py`: 按设备类型填充 nodeProperties。
- `templates.py`: 加载模板，必须返回深拷贝。
- `ids.py`: 生成 ToP ID。

修改入口：

- 图结构问题：优先看 `graph_builder.py`。
- 某个设备参数映射问题：优先看 `property_fillers.py`。
- 组分/物性方法问题：优先看 `assets_builder.py`。
- 项目名、归档信息、固定时间：优先看 `project_builder.py`。

## HSS 加密层

目录：

```text
aspen_to_top/encryption/
```

职责：

- 调用外部 `export-test/hss_file_tool.py`。
- 不改变外部加密逻辑。

关键文件：

- `hss_tool.py`

## 坐标逻辑

坐标从 `.bkp` 文件中读取，逻辑在：

```text
aspen_to_top/utils/layout.py
```

注意：

- 普通设备节点按 block 名读取坐标。
- Source/Sink 也按流股名读取坐标，例如 `S1`、`S2`、`S7`。
- 坐标写入 ToP JSON 的 `processNodes[*].x/y`。

## 标准化 extracted JSON

`*.extracted.json` 是 Aspen 读取层输出，供调试用。

主要结构：

```json
{
  "components": {},
  "blocks": {},
  "streams": {},
  "params": {},
  "methad": "",
  "stream_topology_map": {},
  "processGraph": {
    "nodes": [],
    "edges": []
  }
}
```

## ToP JSON

`*.json` 是最终加密进 HSS 的 JSON，排查 ToP 导入失败时优先看它。

重点检查：

- `omProcessGraph.processNodes`
- `omProcessGraph.processEdges`
- `processEdges[*].source.cell` 是否存在于 `processNodes[*].id`
- `processEdges[*].target.cell` 是否存在于 `processNodes[*].id`
- 节点 ID 是否重复
- Source/Sink 坐标是否保留

## 当前支持的 Aspen 模块

当前代码中已有 extractor/模板映射的模块包括：

- `Flash2`
- `Heater`
- `Compr`
- `Pump`
- `Valve`
- `Mixer`
- `SSplit`
- `FSplit`
- `HeatX`
- `RadFrac`
- `Sep`
- `RecycleBreaker`
- `RStoic`

## 关键设计约束

- 不修改 `export-test/hss_file_tool.py`。
- 不把 ToP 模板字段写到 Aspen 读取层。
- 不把 Aspen COM 路径读取写到 ToP 构建层。
- 新设备优先新增独立文件和注册表。
- 模板加载必须深拷贝，避免多个节点共用同一个 dict。
- 生成 HSS 时保留最终 ToP JSON。
