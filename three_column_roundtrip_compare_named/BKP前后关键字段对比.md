# 三个精馏塔 BKP -> HSS -> BKP 对比

## 乙烯塔

| 字段 | 原始 BKP | trip BKP |
| --- | --- | --- |
| NSTAGE | 174 | 174 |
| CONDENSER | PARTIAL-V | PARTIAL-V |
| VIEW_PRES | PROFILE | TOP/BOTTOM |
| PRES1 | 1720000.0 | 1720000.0 |
| PRES2 | None | 1753000.0 |
| DP_STAGE | None | 888.88888889 |
| BASIS_D | 14.16 | 14.16 |
| BASIS_RR | 197.0 | 197.0 |
| BASIS_RDV | 1.0 | 1.0 |

- FEED_STAGE: 原始 `{}`，trip `{}`
- PROD_STAGE: 原始 `{'3261': 10, '3227': 140, '3256': 174}`，trip `{'3261': 10, '3227': 140, '3256': 174}`
- PROD_PHASE: 原始 `{'3261': 'V', '3227': 'L', '3256': 'L'}`，trip `{'3261': 'V', '3227': 'L', '3256': 'L'}`
- PROD_FLOW: 原始 `{'3261': 1329.0, '3227': 217.0, '3256': None}`，trip `{'3261': 1329.0, '3227': 217.0, '3256': None}`
- SPEC: 原始 `{'SPEC_COMPS\\1\\#0': 'ETHAN-01', 'SPEC_STREAMS\\1\\#0': '3238', 'VALUE\\1': 1.7e-05, 'VARTYPE\\1': 'D', 'VARY_STAGE\\1': 10, 'SPEC_COMPS\\2\\#0': 'ETHYL-01', 'SPEC_STREAMS\\2\\#0': '3256', 'VALUE\\2': 0.005, 'VARTYPE\\2': 'RR', 'VARY_STAGE\\2': None}`，trip `{'SPEC_COMPS\\1\\#0': 'ETHAN-01', 'SPEC_STREAMS\\1\\#0': '3238', 'VALUE\\1': 1.7e-05, 'VARTYPE\\1': 'D', 'VARY_STAGE\\1': 10, 'SPEC_COMPS\\2\\#0': 'ETHYL-01', 'SPEC_STREAMS\\2\\#0': '3256', 'VALUE\\2': 0.005, 'VARTYPE\\2': 'RR', 'VARY_STAGE\\2': None}`

## 脱丁烷塔

| 字段 | 原始 BKP | trip BKP |
| --- | --- | --- |
| NSTAGE | 52 | 52 |
| CONDENSER | TOTAL | TOTAL |
| VIEW_PRES | TOP/BOTTOM | TOP/BOTTOM |
| PRES1 | 450000.0 | 450000.0 |
| PRES2 | 520000.0 | 520000.0 |
| DP_STAGE | 1000.0 | 1000.0 |
| BASIS_D | 185.59 | 185.59 |
| BASIS_RR | 0.13 | 0.13 |
| BASIS_RDV | 0.0 | 0.9 |

- FEED_STAGE: 原始 `{}`，trip `{}`
- PROD_STAGE: 原始 `{'4063': 52}`，trip `{'4063': 52}`
- PROD_PHASE: 原始 `{'4063': 'L'}`，trip `{'4063': 'L'}`
- PROD_FLOW: 原始 `{'4063': None}`，trip `{'4063': None}`
- SPEC: 原始 `{'SPEC_COMPS\\1\\#0': 'N-BUT-01', 'SPEC_STREAMS\\1\\#0': '4063', 'VALUE\\1': 0.0001, 'VARTYPE\\1': 'RR', 'VARY_STAGE\\1': None, 'SPEC_COMPS\\2\\#0': 'METHY-02', 'SPEC_STREAMS\\2\\#0': '4059', 'VALUE\\2': 0.0004, 'VARTYPE\\2': 'D', 'VARY_STAGE\\2': None}`，trip `{'SPEC_COMPS\\1\\#0': 'N-BUT-01', 'SPEC_STREAMS\\1\\#0': '4063', 'VALUE\\1': 0.0001, 'VARTYPE\\1': 'D', 'VARY_STAGE\\1': None, 'SPEC_COMPS\\2\\#0': 'METHY-02', 'SPEC_STREAMS\\2\\#0': '4059', 'VALUE\\2': 0.0004, 'VARTYPE\\2': 'RR', 'VARY_STAGE\\2': None}`

## 丙烯塔

| 字段 | 原始 BKP | trip BKP |
| --- | --- | --- |
| NSTAGE | 277 | 277 |
| CONDENSER | PARTIAL-V | PARTIAL-V |
| VIEW_PRES | TOP/BOTTOM | TOP/BOTTOM |
| PRES1 | 1765000.0 | 1765000.0 |
| PRES2 | 1817000.0 | 1817000.0 |
| DP_STAGE | 992.7 | 992.7 |
| BASIS_D | 15.0 | 15.0 |
| BASIS_RR | 206.0 | 206.0 |
| BASIS_RDV | 1.0 | 1.0 |

- FEED_STAGE: 原始 `{}`，trip `{}`
- PROD_STAGE: 原始 `{'4041': 11, '4051': 277}`，trip `{'4041': 11, '4051': 277}`
- PROD_PHASE: 原始 `{'4041': 'L', '4051': 'L'}`，trip `{'4041': 'L', '4051': 'L'}`
- PROD_FLOW: 原始 `{'4041': 450.0, '4051': None}`，trip `{'4041': 450.0, '4051': None}`
- SPEC: 原始 `{'SPEC_COMPS\\1\\#0': 'PROPA-01', 'SPEC_STREAMS\\1\\#0': '4041', 'VALUE\\1': 0.004, 'VARTYPE\\1': 'D', 'VARY_STAGE\\1': None, 'SPEC_COMPS\\2\\#0': 'PROPY-01', 'SPEC_STREAMS\\2\\#0': '4051', 'VALUE\\2': 0.01, 'VARTYPE\\2': 'RR', 'VARY_STAGE\\2': None}`，trip `{'SPEC_COMPS\\1\\#0': 'PROPA-02', 'SPEC_STREAMS\\1\\#0': '4041', 'VALUE\\1': 0.004, 'VARTYPE\\1': 'D', 'VARY_STAGE\\1': None, 'SPEC_COMPS\\2\\#0': 'PROPY-01', 'SPEC_STREAMS\\2\\#0': '4051', 'VALUE\\2': 0.01, 'VARTYPE\\2': 'RR', 'VARY_STAGE\\2': None}`
