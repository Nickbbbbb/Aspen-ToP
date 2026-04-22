# Aspen-ToP

将 Aspen Plus `.bkp` 文件转换为 ToP 可导入编辑的 `.hss` 文件。

## 快速使用

推荐命令：

```bash
python main.py "aspen_result\flash\flash.bkp" -o output\case.hss -i
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

## 文档

- [项目总览与架构](docs/architecture.md)
- [使用文档](docs/usage.md)
- [开发需求文档](docs/development_requirements.md)
- [文件清理建议](docs/cleanup_plan.md)
- [ToP JSON 构建层说明](aspen_to_top/converter/README.md)

## 核心流程

```text
BKP 文件
  -> Aspen COM 读取
  -> 标准化 Aspen JSON
  -> ToP JSON
  -> export-test/hss_file_tool.py 加密
  -> HSS 文件
```

## 项目结构

```text
aspen_to_top/
  aspen/        Aspen COM 读取层
  converter/    ToP JSON 构建层
  encryption/   HSS 加密适配层
  utils/        坐标、组分映射等工具

Template/       ToP JSON 模板
export-test/    外部 HSS 加密工具
docs/           项目文档
```

## 重要约束

- 不修改 `export-test/hss_file_tool.py`。
- 生成 HSS 时保留最终 ToP JSON，便于排查导入失败。
- 坐标从 `.bkp` 读取，Source/Sink 也按流股名读取坐标。
- 新设备优先通过 extractor、port parser、property filler 注册表扩展。
