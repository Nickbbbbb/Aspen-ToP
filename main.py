from aspen_run import run_and_export
from json_create import create_json
import os

BKP = r"C:\Users\Administrator\Downloads\export-test\aspen_result\hda\hda.bkp"
OUT = "aspen_fixed_data.json"

# 运行 Aspen 导出
run_and_export(BKP, OUT)

create_json()

