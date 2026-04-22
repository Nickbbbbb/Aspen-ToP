# ToP JSON 构建层说明

`converter` 包负责把标准化 Aspen JSON 转换为 ToP JSON。

## 文件职责

- `json_builder.py`: 总编排器，生成 ID 映射，调用各子 builder，写出 JSON。
- `project_builder.py`: 构建 `omProject` 和 `omProcessArchive`。
- `graph_builder.py`: 构建 `omProcessGraph`、`processNodes`、`processEdges`。
- `assets_builder.py`: 构建组分、组分组、物性方法。
- `property_fillers.py`: 按设备类型填充 block 节点的 `nodeProperties`。
- `templates.py`: 加载 ToP 模板，返回深拷贝。
- `ids.py`: 生成 ToP ID。

## 修改入口

新增设备参数映射：

1. 在 `property_fillers.py` 新增 `fill_xxx()`。
2. 在 `PROPERTY_FILLERS` 中注册 Aspen block type。

修改图节点或边结构：

1. 优先修改 `graph_builder.py`。
2. 保证 `processEdges.source.cell` 和 `processEdges.target.cell` 都能在 `processNodes.id` 中找到。

修改组分或物性方法：

1. 优先修改 `assets_builder.py`。
2. 不要把组分逻辑写进 `graph_builder.py`。

修改项目元信息：

1. 优先修改 `project_builder.py`。
2. 不要把固定时间、项目名等字段散落到其他 builder。
