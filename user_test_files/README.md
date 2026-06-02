# 用户测试文件

每个模块文件夹中提供两个测试 case；每个 case 同时包含 `.bkp` 和 `.hss`。

## Column 核心样例

- `column/乙烯塔.bkp` 和 `column/乙烯塔.hss`
- `column/脱丁烷塔.bkp` 和 `column/脱丁烷塔.hss`

## 普通模块

- `flash`
- `heater`
- `valve`
- `pump`
- `mixer`
- `compressor`
- `heatx`
- `splitter_fsplit`

建议先用 `hss-to-bkp` 验证 `column` 两个核心样例，再用批量命令验证其它模块。
