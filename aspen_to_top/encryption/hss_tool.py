import importlib.util
import sys
from pathlib import Path
from types import ModuleType


class HssTool:
    """Adapter for the external export-test HSS encryption tool."""

    _module = None

    @classmethod
    def _load_external_tool(cls) -> ModuleType:
        if cls._module is not None:
            return cls._module

        project_root = Path(__file__).resolve().parents[2]
        tool_path = project_root / "export-test" / "hss_file_tool.py"
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
        """Provide Crypto.Util.Padding when the environment has an older Crypto package."""
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
        """Encrypt a ToP JSON file into HSS using export-test/hss_file_tool.py."""
        if not output_file:
            raise ValueError("未指定输出 HSS 文件")

        module = cls._load_external_tool()
        module.encrypt_json(str(input_file), str(output_file))
        return True

    @classmethod
    def decrypt(cls, input_file: str, output_file: str) -> bool:
        """Decrypt an HSS file into JSON using export-test/hss_file_tool.py."""
        if not output_file:
            raise ValueError("未指定输出 JSON 文件")

        module = cls._load_external_tool()
        module.decrypt_hss(str(input_file), str(output_file))
        return True
