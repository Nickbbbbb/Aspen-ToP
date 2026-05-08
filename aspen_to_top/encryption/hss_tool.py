import importlib.util
import sys
from types import ModuleType

from ..utils.runtime_paths import EXPORT_TOOL_DIR


class HssTool:
    """外部 HSS 加密工具适配器。

    本项目不直接实现 HSS 加密算法，也不修改外部工具。
    真正的加密/解密函数来自：

    export-test/hss_file_tool.py

    这里做的事情只有三件：

    1. 动态加载 export-test/hss_file_tool.py。
    2. 在旧 Crypto 环境中补齐 Crypto.Util.Padding 兼容层。
    3. 对外提供 HssTool.encrypt()/decrypt() 统一入口。
    """

    _module = None

    @classmethod
    def _load_external_tool(cls) -> ModuleType:
        """动态加载 export-test/hss_file_tool.py。

        使用 importlib 动态加载，是因为 export-test 目录名中有短横线，
        不能作为普通 Python 包名 import。
        """
        if cls._module is not None:
            return cls._module

        tool_path = EXPORT_TOOL_DIR / "hss_file_tool.py"
        if not tool_path.exists():
            raise FileNotFoundError(f"HSS 工具不存在: {tool_path}")

        cls._ensure_padding_compat()
        spec = importlib.util.spec_from_file_location("export_test_hss_file_tool", tool_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载 HSS 工具: {tool_path}")

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SystemExit as exc:
            raise RuntimeError(
                "HSS 外部工具初始化失败，请先安装依赖: pip install pycryptodome"
            ) from exc
        cls._module = module
        return module

    @staticmethod
    def _ensure_padding_compat() -> None:
        """兼容旧 Crypto 包。

        部分环境里能 import Crypto.Cipher.AES，但没有 Crypto.Util.Padding。
        外部 hss_file_tool.py 会直接 import pad/unpad，所以这里在 sys.modules
        中临时注册一个最小 PKCS#7 padding 实现，保证外部工具能正常加载。
        """
        if "Crypto.Util.Padding" in sys.modules:
            return

        try:
            __import__("Crypto.Util.Padding")
            return
        except ImportError:
            pass

        padding_module = ModuleType("Crypto.Util.Padding")

        def pad(data_to_pad: bytes, block_size: int, style: str = "pkcs7") -> bytes:
            if style != "pkcs7":
                raise ValueError("Only pkcs7 padding is supported")
            padding_len = block_size - len(data_to_pad) % block_size
            return data_to_pad + bytes([padding_len]) * padding_len

        def unpad(padded_data: bytes, block_size: int, style: str = "pkcs7") -> bytes:
            if style != "pkcs7":
                raise ValueError("Only pkcs7 padding is supported")
            if not padded_data or len(padded_data) % block_size:
                raise ValueError("Input data is not padded")
            padding_len = padded_data[-1]
            if padding_len < 1 or padding_len > min(block_size, len(padded_data)):
                raise ValueError("Padding is incorrect")
            if padded_data[-padding_len:] != bytes([padding_len]) * padding_len:
                raise ValueError("PKCS#7 padding is incorrect")
            return padded_data[:-padding_len]

        padding_module.pad = pad
        padding_module.unpad = unpad
        sys.modules["Crypto.Util.Padding"] = padding_module

    @classmethod
    def encrypt(cls, input_file: str, output_file: str) -> bool:
        """把 ToP JSON 加密为 HSS。

        input_file 必须是最终 ToP JSON，不是 extracted JSON。
        """
        if not output_file:
            raise ValueError("未指定输出 HSS 文件")

        module = cls._load_external_tool()
        module.encrypt_json(str(input_file), str(output_file))
        return True

    @classmethod
    def decrypt(cls, input_file: str, output_file: str) -> bool:
        """把 HSS 解密为 JSON，主要用于调试导入失败问题。"""
        if not output_file:
            raise ValueError("未指定输出 JSON 文件")

        module = cls._load_external_tool()
        module.decrypt_hss(str(input_file), str(output_file))
        return True
