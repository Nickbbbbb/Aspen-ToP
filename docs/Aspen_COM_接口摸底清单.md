# Aspen COM 接口摸底清单

这份清单基于当前机器实际探测结果整理，目标是给后续 `标准化 Aspen JSON -> Aspen COM 建模 -> .bkp` 提供一份可执行的起点，而不是只靠记忆猜接口。

## 结论摘要

- `Apwn.Document` 顶层已经确认支持 `InitNew`、`InitFromArchive2`、`SaveAs`、`WriteArchive2`、`Run2`、`Tree`、`Engine` 等关键能力。
- `Tree` / `Node` 层已经确认支持 `FindNode`、`Elements`、`SetValue`、`SetValueAndUnit`、`SetValueUnitAndBasis`、`SetAttributeValue`、`Delete`、`RemoveAll`。
- 进一步探测时还发现了 `NewChild`、`NewID`，它们很可能和“从空白 flowsheet 创建对象”相关，后面值得优先实验。
- 从真实样例看，`\\Data` 根节点存在，且包含 `Components / Properties / Flowsheet / Streams / Blocks` 等主分区。
- 一个实用细节是：很多节点用“逐层下钻”更稳，例如 `tree.FindNode("\\Data").FindNode("Blocks")`，而不是一次性绝对路径打到深层。

## 已确认的 `Apwn.Document` 关键方法

当前机器探测到的高价值方法如下：

```text
AutoSave
Close
CloseDocument
CreateRouteTree
Engine
EngineServer
EngineSimulation
GetNew
GetNew3
InitFromArchive
InitFromArchive2
InitFromArchive3
InitFromFile
InitFromFile2
InitFromTemplate
InitFromTemplate2
InitFromXML
InitNew
InitNew2
New
New2
New3
NewAsync
NewSelection
Quit
Reinit
Run
Run2
RunScript
Save
Save2
SaveAs
SaveAs2
SaveLink
SaveSelection
Tree
Visible
WriteArchive
WriteArchive2
```

对我们最关键的是：

- 建新模型：`InitNew`
- 打开已有归档：`InitFromArchive2`
- 重算：`Reinit`、`Run2`
- 保存：`Save`、`SaveAs`、`WriteArchive2`
- 访问对象树：`Tree`

## 已确认的 `Tree` / `Node` 能力

当前机器上 `Tree` 和 `\\Data\\Blocks` 节点可见的高价值方法包括：

```text
AddClassAttribute
AttributeType
AttributeValue
ClassAttributeType
ClassAttributeValue
Delete
DeleteClassAttribute
Elements
FindNode
GetValue
HasAttribute
HasClassAttribute
NewChild
NewID
RemoveAll
SetAttributeValue
SetClassAttributeValue
SetName
SetValue
SetValueAndUnit
SetValueUnitAndBasis
Value
ValueForUnit
ValueType
```

对后续建模最重要的是：

- 找节点：`FindNode`
- 枚举子节点：`Elements`
- 写值：`SetValue` / `SetValueAndUnit` / `SetValueUnitAndBasis`
- 改属性：`SetAttributeValue`
- 删除内容：`Delete` / `RemoveAll`

## `InitNew()` 后 `\\Data` 根节点结构

新建空白流程后，`\\Data` 下面已经存在这些主分区：

```text
Pure Databanks
Other Databanks
Components
Properties
Flowsheet
Streams
Blocks
Sensors
Controllers
Unit Procedures
Utilities
Reactions
Convergence
Costing
Flowsheeting Options
Model Analysis Tools
EO Configuration
Results Summary
Dynamic Configuration
PSValve
PSVScenario
PSVTank
Data-Service
Train-Set
```

这说明 Aspen 至少给了我们一棵稳定的顶层骨架，后面不一定需要“手动创建所有一级目录”。

## 真实样例归档的树结构

探测样例：`examples/single_bkp/alkane.bkp`

在真实归档里，`\\Data` 下的主分区和典型内容如下：

### `Components`

```text
Assay/Blend
LightEndProperties
PetroCharacterization
Pseudocomponents
Attr-Comps
Henry-Comps
Moisture-Comps
UNIFAC-Groups
Comp-Groups
Comp-Lists
Polymers
Attr-Scaling
Bio-Comps
```

### `Properties`

```text
Property Methods
Estimation
Molecular Structure
Parameters
Data
Analysis
Prop-Sets
Advanced
CO-Package
```

### `Flowsheet`

```text
Def-Streams
Custom Forms
Batch Process Plots
```

### `Streams`

样例中的流股名：

```text
ABCDE
B
BC
BCDE
C
D
DE
E
```

### `Blocks`

样例中的模块名：

```text
B2
B3
B4
```

### `Properties -> Specifications -> Input`

这一路径已经确认可访问，常见输入项包括：

```text
User Table
User Tree
BASEOPSET
BOPSETNAME
CHEMISTRY
EOSSETNO
FMODIFY
FREE_WATER
GBASEOPSET
GCHEMISTRY
GEOSSETNO
GFREE_WATER
GHEATOFMIX
GHEN
GISEOS
GLGAMMASETNO
GLIQDENSITY
GLIQENTHALPY
GLIQGAMMA
GLIQREFSTATE
```

这里和我们前向提取里用到的 `GBASEOPSET` 是对上的。

## 一个重要经验

对于较深路径，建议优先用逐层访问：

```python
data = tree.FindNode("\\Data")
blocks = data.FindNode("Blocks")
properties = data.FindNode("Properties")
prop_input = properties.FindNode("Specifications").FindNode("Input")
```

不要默认深层绝对路径一定稳定。例如同一会话里，`tree.FindNode("\\Data\\Blocks")` 可能拿不到节点，但 `tree.FindNode("\\Data").FindNode("Blocks")` 可以成功。

这意味着后续实现建模器时，节点访问层最好统一封装成：

- 先拿根节点
- 再逐层 `FindNode`
- 每层都做空值保护和诊断日志

## 当前对“从零建模”的判断

现在已经能确认：

- 能新建 Aspen 文档
- 能访问和修改 Tree
- 能重算
- 能保存归档

但还没有确认这些更细的建模问题：

- 如何通过 COM 从空白文档里创建新的 block 和 stream
- 是否必须通过特定 flowsheet 节点或脚本命令创建单元
- 创建后 block type 与端口是如何挂到 Tree 上的
- 哪些对象必须由 Aspen 内部先创建，再允许 `SetValue`

因此，当前最稳路线仍然是两阶段：

1. 简单单元先走“文本 `.bkp` 生成”或“模板 `.bkp` 复制后回填”。
2. 并行摸清 Aspen 的“创建对象”接口，再逐步替换成真正的 COM 建模。

## 推荐的下一步验证

建议按这个顺序做最小试验：

1. `InitNew()` 后确认如何设置物性方法。
2. 确认是否能创建 1 个 `Flash2` block 和 1 条进料、2 条产品流股。
3. 确认创建后 `\\Data\\Blocks\\<name>\\Input`、`Ports` 是否自动出现。
4. 写入 `TEMP/PRES/TOTFLOW/FLOW`，跑一次 `Run2`。
5. 用 `SaveAs` 或 `WriteArchive2` 输出 `.bkp`。

## 复用脚本

仓库里已经补了一份探测脚本：

[inspect_aspen_com.py](C:/Users/Administrator/Downloads/Aspen-ToP/scripts/inspect_aspen_com.py)

用法：

```bash
python scripts/inspect_aspen_com.py
python scripts/inspect_aspen_com.py --bkp examples\single_bkp\alkane.bkp
python scripts/inspect_aspen_com.py --bkp examples\single_bkp\alkane.bkp --output output\aspen_com_probe.json
```

这份脚本会输出：

- `Apwn.Document` 的关键方法
- `InitNew()` 后 `\\Data` 的根结构
- 指定 `.bkp` 的主分区、样例 block、样例 stream 和典型输入节点
