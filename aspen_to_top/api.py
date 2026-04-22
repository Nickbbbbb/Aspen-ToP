from pathlib import Path
from typing import List, Optional, Union

from .main import AspenToTopConverter


def convert_bkp_to_hss(
    bkp_files: Union[str, Path, List[Union[str, Path]]],
    output_dir: Optional[Union[str, Path]] = None,
    save_intermediate: bool = False
) -> List[str]:
    """
    将 Aspen BKP 文件转换为 ToP HSS 文件

    Args:
        bkp_files: BKP 文件路径或文件路径列表
        output_dir: 输出目录，默认为 BKP 文件所在目录
        save_intermediate: 是否保存中间 JSON 文件

    Returns:
        转换后的 HSS 文件路径列表

    Example:
        # 单个文件
        hss_file = convert_bkp_to_hss("flash.bkp")
        
        # 批量文件
        hss_files = convert_bkp_to_hss(["flash1.bkp", "flash2.bkp"])
        
        # 指定输出目录
        hss_files = convert_bkp_to_hss("flash.bkp", output_dir="output")
    """
    if isinstance(bkp_files, (str, Path)):
        bkp_files = [bkp_files]

    hss_files = []
    converter = AspenToTopConverter()

    for bkp_file in bkp_files:
        bkp_path = Path(bkp_file)
        if not bkp_path.exists():
            print(f"❌ 文件不存在: {bkp_path}")
            continue

        base_output_dir = Path(output_dir) if output_dir else bkp_path.parent
        output_hss = base_output_dir / f"{bkp_path.stem}.hss"

        try:
            result = converter.convert(
                str(bkp_path),
                output_hss=str(output_hss),
                save_intermediate=save_intermediate,
                output_dir=str(base_output_dir),
            )
            hss_files.append(result["hss"])
        except Exception as e:
            print(f"❌ 转换失败 {bkp_path}: {e}")

    return hss_files


def extract_bkp_data(
    bkp_file: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    """
    仅提取 BKP 文件数据到 JSON

    Args:
        bkp_file: BKP 文件路径
        output_json: 输出 JSON 文件路径

    Returns:
        提取后的 JSON 文件路径
    """
    converter = AspenToTopConverter()
    return converter.extract_only(str(bkp_file), str(output_json) if output_json else None)


def build_top_json(
    input_json: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    """
    仅构建 ToP JSON 文件

    Args:
        input_json: 输入 JSON 文件路径
        output_json: 输出 JSON 文件路径

    Returns:
        构建后的 JSON 文件路径
    """
    converter = AspenToTopConverter()
    return converter.build_only(str(input_json), str(output_json) if output_json else None)


def encrypt_to_hss(
    input_json: Union[str, Path],
    output_hss: Optional[Union[str, Path]] = None
) -> str:
    """
    仅加密 JSON 文件为 HSS

    Args:
        input_json: 输入 JSON 文件路径
        output_hss: 输出 HSS 文件路径

    Returns:
        加密后的 HSS 文件路径
    """
    converter = AspenToTopConverter()
    return converter.encrypt_only(str(input_json), str(output_hss) if output_hss else None)


def decrypt_hss(
    hss_file: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None
) -> str:
    """
    解密 HSS 文件为 JSON

    Args:
        hss_file: HSS 文件路径
        output_json: 输出 JSON 文件路径

    Returns:
        解密后的 JSON 文件路径
    """
    from .encryption.hss_tool import HssTool
    target_json = str(output_json) if output_json else str(Path(hss_file).with_suffix(".json"))
    HssTool.decrypt(str(hss_file), target_json)
    return target_json
