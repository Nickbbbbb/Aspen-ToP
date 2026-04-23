"""对外暴露的最小转换接口。

业务侧同学通常只需要使用这里的两个函数：

- convert_single_bkp(bkp_file): 转换单个 BKP 文件。
- convert_bkp_folder(folder): 批量转换某个文件夹下的 BKP 文件。

两个函数都使用固定输出目录 PROJECT_ROOT/output，并按 BKP 文件同名生成：

- <name>.hss
- <name>.json
- <name>.extracted.json

其它函数保留给调试或过渡调用使用，不建议作为新业务入口。
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from .main import AspenToTopConverter, PROJECT_ROOT


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def convert_single_bkp(bkp_file: Union[str, Path], save_intermediate: bool = True) -> Dict[str, Optional[str]]:
    """转换单个 Aspen BKP 文件。

    参数：
        bkp_file: Aspen `.bkp` 文件路径。
        save_intermediate: 是否保留 Aspen 提取阶段生成的标准化 JSON。

    返回：
        包含 `hss`、`top_json`、`extract_json` 路径的字典。

    输出规则：
        output/<bkp_stem>.hss
        output/<bkp_stem>.json
        output/<bkp_stem>.extracted.json
    """
    # 对外接口尽量少暴露参数：调用方只传 BKP 路径即可。
    # 输出目录和输出文件名在这里统一约定，避免不同调用方各自拼路径造成混乱。
    bkp_path = Path(bkp_file).resolve()
    if not bkp_path.exists():
        raise FileNotFoundError(f"BKP 文件不存在: {bkp_path}")
    if bkp_path.suffix.lower() != ".bkp":
        raise ValueError(f"输入文件不是 .bkp: {bkp_path}")

    # HSS 输出路径决定另外两个中间文件路径：
    # output/foo.hss -> output/foo.json -> output/foo.extracted.json
    output_hss = DEFAULT_OUTPUT_DIR / f"{bkp_path.stem}.hss"
    converter = AspenToTopConverter()
    return converter.convert(
        str(bkp_path),
        output_hss=str(output_hss),
        save_intermediate=save_intermediate,
        output_dir=str(DEFAULT_OUTPUT_DIR),
    )


def convert_bkp_folder(folder: Union[str, Path], save_intermediate: bool = True) -> List[Dict[str, Optional[str]]]:
    """批量转换文件夹第一层的 Aspen BKP 文件。

    参数：
        folder: 包含 `.bkp` 文件的文件夹路径。
        save_intermediate: 是否保留 Aspen 提取阶段生成的标准化 JSON。

    返回：
        每个 BKP 文件对应一个转换结果字典。

    输出规则：
        对每个 <name>.bkp 生成：
        output/<name>.hss
        output/<name>.json
        output/<name>.extracted.json
    """
    folder_path = Path(folder).resolve()
    if not folder_path.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder_path}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"输入路径不是文件夹: {folder_path}")

    # 默认只扫描文件夹第一层的 .bkp，避免递归时把备份目录和临时目录也纳入转换。
    # 如需递归扫描，可以把 glob("*.bkp") 改为 rglob("*.bkp")。
    bkp_files = sorted(folder_path.glob("*.bkp"))
    if not bkp_files:
        raise FileNotFoundError(f"文件夹中没有 .bkp 文件: {folder_path}")

    return [convert_single_bkp(bkp_file, save_intermediate=save_intermediate) for bkp_file in bkp_files]


def convert_bkp_to_hss(
    bkp_files: Union[str, Path, List[Union[str, Path]]],
    output_dir: Optional[Union[str, Path]] = None,
    save_intermediate: bool = False
) -> List[str]:
    """过渡接口；业务代码建议使用 convert_single_bkp 或 convert_bkp_folder。"""
    if isinstance(bkp_files, (str, Path)):
        bkp_files = [bkp_files]

    hss_files = []
    converter = AspenToTopConverter()
    base_output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_OUTPUT_DIR

    for bkp_file in bkp_files:
        bkp_path = Path(bkp_file).resolve()
        if not bkp_path.exists():
            print(f"❌ 文件不存在: {bkp_path}")
            continue

        output_hss = base_output_dir / f"{bkp_path.stem}.hss"
        try:
            result = converter.convert(
                str(bkp_path),
                output_hss=str(output_hss),
                save_intermediate=save_intermediate,
                output_dir=str(base_output_dir),
            )
            hss_files.append(result["hss"])
        except Exception as exc:
            print(f"❌ 转换失败 {bkp_path}: {exc}")

    return hss_files


def extract_bkp_data(
    bkp_file: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    converter = AspenToTopConverter()
    return converter.extract_only(str(bkp_file), str(output_json) if output_json else None)


def build_top_json(
    input_json: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    converter = AspenToTopConverter()
    return converter.build_only(str(input_json), str(output_json) if output_json else None)


def encrypt_to_hss(
    input_json: Union[str, Path],
    output_hss: Optional[Union[str, Path]] = None
) -> str:
    converter = AspenToTopConverter()
    return converter.encrypt_only(str(input_json), str(output_hss) if output_hss else None)


def decrypt_hss(
    hss_file: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    from .encryption.hss_tool import HssTool
    target_json = str(output_json) if output_json else str(Path(hss_file).with_suffix(".json"))
    HssTool.decrypt(str(hss_file), target_json)
    return target_json
