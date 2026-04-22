# Aspen-ToP 使用文档

## 环境要求

- Windows
- 已安装 Aspen Plus，并且 COM 接口可用
- Python 环境可导入：
  - `pythoncom`
  - `win32com.client`
  - `Crypto`

HSS 加密依赖外部工具 `export-test/hss_file_tool.py`。如果加密时报缺少 `pycryptodome`，安装：

```bash
python -m pip install pycryptodome
```

如果机器上有多个 Python，请确认安装到实际运行 `python main.py` 的那个 Python 环境。

## 最推荐用法

把 BKP 转为 HSS，同时保留可检查 JSON：

```bash
python main.py "C:\path\to\case.bkp" -o output\case.hss -i
```

输出：

```text
output\case.hss
output\case.json
output\case.extracted.json
```

说明：

- `case.hss`: ToP 导入文件。
- `case.json`: 最终 ToP JSON，也就是被加密进 HSS 的内容。
- `case.extracted.json`: Aspen COM 提取后的标准化中间数据。

## 一键转换

```bash
python main.py aspen_result\flash\flash.bkp
```

默认输出到：

```text
test_output\flash.hss
test_output\flash.json
```

指定输出路径：

```bash
python main.py aspen_result\flash\flash.bkp -o output\flash.hss
```

这会同时生成：

```text
output\flash.hss
output\flash.json
```

## 批量转换

```bash
python main.py a.bkp b.bkp -d output
```

批量转换时不要使用 `-o`，因为 `-o` 是单个 HSS 文件路径。

## 分步调试

### 只提取 Aspen 数据

```bash
python main.py case.bkp --extract-only output\case.extracted.json
```

用于检查 Aspen COM 读取是否正确。

重点看：

- `components`
- `blocks`
- `streams`
- `methad`
- `processGraph`

### 只构建 ToP JSON

```bash
python main.py --build-only output\case.extracted.json --top-json output\case.json
```

用于检查 ToP JSON 构建是否正确，不需要重新打开 Aspen。

### 只加密 HSS

```bash
python main.py --encrypt-only output\case.json -o output\case.hss
```

用于确认是否是加密阶段导致 HSS 导入失败。

### 解密 HSS

```bash
python main.py --decrypt output\case.hss output\case.decrypted.json
```

用于验证 HSS 中实际内容。

## Python API

```python
from aspen_to_top import convert_bkp_to_hss

convert_bkp_to_hss(
    "aspen_result/flash/flash.bkp",
    output_dir="output",
    save_intermediate=True,
)
```

分步 API：

```python
from aspen_to_top import extract_bkp_data, build_top_json, encrypt_to_hss

extract_bkp_data("case.bkp", "output/case.extracted.json")
build_top_json("output/case.extracted.json", "output/case.json")
encrypt_to_hss("output/case.json", "output/case.hss")
```

## ToP 导入失败时的排查顺序

1. 先看 `output\case.json` 是否能正常打开、是否是合法 JSON。
2. 检查 `omProcessGraph.processNodes` 中节点 ID 是否重复。
3. 检查每条 `processEdges.source.cell` 和 `processEdges.target.cell` 是否能在节点 ID 中找到。
4. 检查 Source/Sink 坐标是否为从 BKP 读取出来的值，而不是全部 0。
5. 检查设备 `nodeProperties` 是否缺关键字段。
6. 使用 `--decrypt` 解密 HSS，确认 HSS 中内容与 `case.json` 一致。

## 常见问题

### 运行时找不到 BKP

确认路径存在，路径里有中文或空格时加引号：

```bash
python main.py "C:\Users\Administrator\Downloads\Aspen-ToP\aspen_result\flash\flash.bkp" -o output\case.hss -i
```

### 加密时报 Crypto 相关错误

先确认当前 Python：

```bash
python -c "import sys; print(sys.executable)"
```

然后给这个 Python 安装：

```bash
python -m pip install pycryptodome
```

### Aspen 打开失败

检查：

- Aspen Plus 是否安装。
- BKP 文件是否能手动打开。
- 当前用户是否有 COM 权限。
- 是否有残留 Aspen 进程占用。

## 推荐输出目录

建议所有运行结果都放在：

```text
output/
```

调试结果和临时结果不要提交到版本库。
