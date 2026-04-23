from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aspen_to_top import convert_bkp_folder, convert_single_bkp


EXAMPLES_DIR = Path(__file__).resolve().parent
def run_single():
    bkp_file = EXAMPLES_DIR / "single_bkp" / "镇海乙烯全流程.bkp"
    result = convert_single_bkp(bkp_file)
    print("单文件转换完成:")
    print_result(result)


def run_batch():
    folder = EXAMPLES_DIR / "batch_bkp"
    result = convert_bkp_folder(folder)
    print("批量转换完成:")
    for item in result:
        print_result(item)


def print_result(result):
    for key in ("hss", "top_json", "extract_json"):
        if result.get(key):
            print(f"{key}: {result[key]}")


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    if mode == "single":
        run_single()
    elif mode == "batch":
        run_batch()
    elif mode == "all":
        # run_single()
        run_batch()
    else:
        print("用法: python examples\\demo_convert.py [single|batch|all]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
