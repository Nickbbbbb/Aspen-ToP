# Roundtrip Summary

| Sample | BKP -> HSS | HSS -> BKP | Note |
|---|---|---|---|
| mixer_test | OK | OK | Roundtrip BKP generated successfully. |
| 乙烯塔 | OK | FAIL | HSS -> BKP failed: This minimal BKP builder only supports ['Compr', 'FSplit', 'Flash2', 'HeatX', 'Heater', 'Mixer', 'Pump', 'SSplit', 'Valve']; found unsupported block types: ['RadFrac'] |
| 脱丁烷塔 | OK | FAIL | HSS -> BKP failed: This minimal BKP builder only supports ['Compr', 'FSplit', 'Flash2', 'HeatX', 'Heater', 'Mixer', 'Pump', 'SSplit', 'Valve']; found unsupported block types: ['RadFrac'] |
| alkane | OK | FAIL | HSS -> BKP failed: This minimal BKP builder only supports ['Compr', 'FSplit', 'Flash2', 'HeatX', 'Heater', 'Mixer', 'Pump', 'SSplit', 'Valve']; found unsupported block types: ['RadFrac'] |
| 镇海三联塔（430-431-440） | OK | FAIL | HSS -> BKP failed: This minimal BKP builder only supports ['Compr', 'FSplit', 'Flash2', 'HeatX', 'Heater', 'Mixer', 'Pump', 'SSplit', 'Valve']; found unsupported block types: ['RadFrac'] |
| 镇海乙烯全流程 | OK | FAIL | HSS -> BKP failed: This minimal BKP builder only supports ['Compr', 'FSplit', 'Flash2', 'HeatX', 'Heater', 'Mixer', 'Pump', 'SSplit', 'Valve']; found unsupported block types: ['RStoic', 'RadFrac', 'Sep'] |
