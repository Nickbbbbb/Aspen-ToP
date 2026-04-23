import os
import pythoncom
import win32com.client


class AspenConnector:
    """Aspen Plus COM 接口连接器。

    Aspen 的 .bkp 文件不是普通 JSON/XML，不能直接用文本解析得到完整流程信息。
    本项目通过 Windows COM 自动化启动 Aspen Plus，再调用 Aspen 自己的
    InitFromArchive2() 打开 .bkp，最后从 aspen.Tree 读取流程数据。

    典型 COM 调用顺序：

    1. pythoncom.CoInitialize()
    2. win32com.client.Dispatch("Apwn.Document")
    3. aspen.InitFromArchive2(<bkp path>)
    4. tree = aspen.Tree
    5. tree.FindNode(r"\\Data\\...")
    6. aspen.Close()/Quit(), pythoncom.CoUninitialize()
    """

    def __init__(self, bkp_file_path: str):
        self.bkp_path = os.path.abspath(bkp_file_path)
        self.aspen = None
        self.tree = None

    def connect(self) -> bool:
        if not os.path.exists(self.bkp_path):
            raise FileNotFoundError(f"文件未找到: {self.bkp_path}")
        print(f"正在启动 Aspen Plus...")
        try:
            # COM 在当前线程初始化。没有这一步，某些 Python/Windows 环境会无法调 Aspen。
            pythoncom.CoInitialize()
            # "Apwn.Document" 是 Aspen Plus 暴露的 COM ProgID。
            self.aspen = win32com.client.Dispatch("Apwn.Document")
            # InitFromArchive2 用 Aspen 自己的能力打开 .bkp 归档文件。
            self.aspen.InitFromArchive2(self.bkp_path)
            self.aspen.Visible = True
            # 尽量压制 Aspen 弹窗，避免批量转换时阻塞。
            self.aspen.SuppressDialogs = 1
            # 后续所有数据读取都围绕这个 Tree 展开。
            self.tree = self.aspen.Tree
            print(f"Aspen Plus 连接成功")
            return True
        except Exception as e:
            print(f"初始化失败: {e}")
            self.disconnect()
            raise

    def disconnect(self):
        """关闭 Aspen 文档并释放 COM。

        finally 中调用它很重要，否则 Aspen 进程可能残留，影响下一次批量转换。
        """
        if self.aspen:
            try:
                self.aspen.Close()
                self.aspen.Quit()
            except:
                pass
        pythoncom.CoUninitialize()

    def get_tree(self):
        return self.tree
