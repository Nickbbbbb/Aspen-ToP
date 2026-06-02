# Aspen-ToP

将 Aspen Plus `.bkp` 文件转换为 ToP 可导入编辑的 `.hss` 文件。

## 快速使用

推荐命令：

```bash
python main.py "examples\single_bkp\flash.bkp" -o output\case.hss -i
```

输出：

```text
output\case.hss
output\case.json
output\case.extracted.json
```

说明：

- `case.hss`: ToP 导入文件。
- `case.json`: 最终加密进 HSS 的 ToP JSON。
- `case.extracted.json`: Aspen COM 提取后的标准化 JSON。

## EXE 命令行使用

项目支持打包为 `AspenToTop.exe` 后直接运行：

```bat
AspenToTop.exe "C:\path\demo.bkp" -i
AspenToTop.exe "C:\path\bkp_folder" -d "C:\path\output"
```

打包说明见：

- [可执行文件打包说明](docs/可执行文件打包说明.md)

## 文档

- [项目总览](docs/项目总览.md)
- [使用说明](docs/使用说明.md)
- [转换链路开发详解](docs/转换链路开发详解.md)
- [Aspen COM 接口摸底清单](docs/Aspen_COM_接口摸底清单.md)
- [开发规范](docs/开发规范.md)
- [可执行文件打包说明](docs/可执行文件打包说明.md)
- [文件清理说明](docs/文件清理说明.md)
- [ToP JSON 构建层说明](aspen_to_top/converter/构建层说明.md)
- [示例说明](examples/示例说明.md)

## 核心流程

```text
BKP 文件
  -> Aspen COM 读取
  -> 标准化 Aspen JSON
  -> ToP JSON
  -> export-test/hss_file_tool.py 加密
  -> HSS 文件
```

反向恢复链路：

```text
HSS 文件
  -> 解密为 ToP JSON
  -> 恢复为标准化 Aspen JSON
```

最小 BKP 回生链路：

```text
标准化 Aspen JSON
  -> 生成最小可用 BKP 文本归档
```

常用命令：

```bash
python main.py --decrypt output\case.hss output\case.decrypted.json
python main.py --top-to-extract output\case.json output\case.recovered.extracted.json
python main.py --hss-to-extract output\case.hss output\case.recovered.extracted.json
python main.py --extract-to-bkp output\case.extracted.json output\case.regenerated.bkp
python main.py --extract-to-bkp-com output\case.extracted.json output\case.regenerated.bkp --run-regenerated
```

当前边界：

- 现在已经支持 `HSS -> ToP JSON -> 标准化 Aspen JSON`。
- 现在还支持 `标准化 Aspen JSON -> 最小可用 BKP`，当前只覆盖简单单元。
- 现在还支持在骨架 BKP 上用 Aspen COM 回填简单单元参数。
- 还没有直接生成 Aspen `.bkp`。
- 如果要真正输出 `.bkp`，还需要补 Aspen COM 自动建模与 `SaveAs/WriteArchive` 流程。

## 项目结构

```text
aspen_to_top/
  aspen/        Aspen COM 读取层
  converter/    ToP JSON 构建层
  encryption/   HSS 加密适配层
  reverse/      ToP JSON/HSS 反向恢复层
  utils/        坐标、组分映射等工具

Template/       ToP JSON 模板
export-test/    外部 HSS 加密工具
examples/       单文件和批量转换示例
docs/           项目文档
```

## 重要约束

- 不修改 `export-test/hss_file_tool.py`。
- 生成 HSS 时保留最终 ToP JSON，便于排查导入失败。
- 坐标从 `.bkp` 读取，Source/Sink 也按流股名读取坐标。
- 新设备优先通过 extractor、port parser、property filler 注册表扩展。

## 对外接口

推荐只暴露两个转换函数：

```python
from aspen_to_top import convert_single_bkp, convert_bkp_folder

convert_single_bkp("examples/single_bkp/flash.bkp")
convert_bkp_folder("examples/batch_bkp")
```

默认输出到项目根目录 `output/`，文件名与 BKP 同名。
