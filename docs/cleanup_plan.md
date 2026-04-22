# 文件清理建议

本文档只给清理建议，不代表已经删除这些文件。

## 必须保留

这些是当前主流程依赖的文件和目录。

```text
main.py
run.bat
README.md
aspen_to_top/
Template/
export-test/hss_file_tool.py
docs/
```

说明：

- `main.py`: 根目录 CLI 入口。
- `run.bat`: Windows 下便捷入口，可以保留。
- `aspen_to_top/`: 当前主代码。
- `Template/`: ToP JSON 模板，运行必需。
- `export-test/hss_file_tool.py`: 外部 HSS 加密工具，运行必需。
- `docs/`: 项目文档。

## 建议保留但不要提交大量样例

```text
aspen_result/
```

说明：

- 这是 Aspen 测试样例和历史运行文件目录。
- 开发时至少保留少量典型 `.bkp` 用例，例如：
  - flash
  - pump
  - heater
  - column
  - heatx
  - splitter
  - component splitter
- 大型 `.apw`、`.appdf`、`.his`、`.dmp`、Aspen 临时文件可以考虑从仓库移除，只本地保留。

## 可以清理的缓存和系统文件

这些文件由 Python、IDE、macOS 或测试工具生成，通常可以删除。

```text
__pycache__/
aspen_to_top/**/__pycache__/
export-test/__pycache__/
.pytest_cache/
__MACOSX/
```

如果使用 Git，建议加入 `.gitignore`。

## IDE 本地配置

```text
.idea/
```

说明：

- 如果团队统一使用 PyCharm，可以保留少量项目配置。
- 如果不是团队共享配置，建议不提交 `.idea/workspace.xml`。
- `workspace.xml` 通常是个人本地状态，建议删除或忽略。

## 当前主流程不再依赖的旧脚本

这些文件属于早期单文件脚本或调试脚本。当前主流程已迁移到 `aspen_to_top/` 包中。

建议移动到 `legacy/` 或删除前先备份：

```text
aspen_run.py
json_create.py
get_x_y.py
layout_fixed.py
hss_file_tool.py
test.py
test_aspen_result.py
```

说明：

- `aspen_run.py`: 旧版 Aspen COM 提取脚本，功能已迁移到 `aspen_to_top/aspen/`。
- `json_create.py`: 旧版 ToP JSON 构建脚本，功能已迁移到 `aspen_to_top/converter/`。
- `get_x_y.py`: 旧版坐标读取脚本，功能已迁移到 `aspen_to_top/utils/layout.py`。
- `layout_fixed.py`: 旧版布局修复脚本，当前主流程不依赖。
- 根目录 `hss_file_tool.py`: 与 `export-test/hss_file_tool.py` 重复；当前主流程调用 `export-test/hss_file_tool.py`。
- `test.py`、`test_aspen_result.py`: 临时测试脚本，建议整理成正式 pytest 后再保留。

如果担心丢失历史逻辑，推荐先移动：

```text
legacy/
  aspen_run.py
  json_create.py
  get_x_y.py
  layout_fixed.py
  hss_file_tool.py
```

## 可清理的历史 JSON/HSS 输出

这些多半是运行输出或调试产物，不是源码。

```text
aspen_fixed_data.json
final_result.json
process_edges.json
process_nodes.json
output/
test_output/
export-test/*.json
export-test/*.hss
```

注意：

- `export-test/hss_file_tool.py` 必须保留。
- `export-test` 下的样例 JSON/HSS 如果用于对照测试，可以保留少量。
- `output/` 和 `test_output/` 推荐加入 `.gitignore`。

## aspen_to_top 内部疑似误放文件

当前看到：

```text
aspen_to_top/flash.bkp
aspen_to_top/flash_three_test.bkp
aspen_to_top/output/
```

建议：

- `.bkp` 样例不要放在源码包里，移动到 `aspen_result/` 或 `samples/`。
- `aspen_to_top/output/` 是运行输出，不应放在包目录中。

## constants 目录

```text
constants/
```

说明：

- 旧脚本 `aspen_run.py`、`json_create.py` 依赖它。
- 新代码使用 `aspen_to_top/utils/chemical_mapper.py`。
- 如果删除旧脚本，`constants/` 大概率也可以删除。
- 删除前确认没有外部脚本还在 import `constants`。

## 推荐 .gitignore

建议新增或更新 `.gitignore`：

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.idea/workspace.xml
__MACOSX/

output/
test_output/
aspen_to_top/output/

*.hss
*.decrypted.json
*.extracted.json

aspen_result/**/*.apw
aspen_result/**/*.appdf
aspen_result/**/*.his
aspen_result/**/*.for
aspen_result/**/*.dmp
```

是否忽略 `.bkp` 取决于团队是否要把样例流程文件纳入仓库。

## 推荐清理步骤

1. 先创建 `legacy/`，移动旧脚本，不直接删除。
2. 跑一次完整转换：

```bash
python main.py "aspen_result\flash\flash.bkp" -o output\case.hss -i
```

3. 确认 ToP 可以导入 `output\case.hss`。
4. 再删除缓存、历史输出、IDE 本地文件。
5. 最后再决定是否删除 `legacy/`。
