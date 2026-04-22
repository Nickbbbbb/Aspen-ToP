import os
import pythoncom
import win32com.client


class AspenConnector:
    """Aspen Plus COM 接口连接器"""

    def __init__(self, bkp_file_path: str):
        self.bkp_path = os.path.abspath(bkp_file_path)
        self.aspen = None
        self.tree = None

    def connect(self) -> bool:
        if not os.path.exists(self.bkp_path):
            raise FileNotFoundError(f"文件未找到: {self.bkp_path}")
        print(f"正在启动 Aspen Plus...")
        try:
            pythoncom.CoInitialize()
            self.aspen = win32com.client.Dispatch("Apwn.Document")
            self.aspen.InitFromArchive2(self.bkp_path)
            self.aspen.Visible = True
            self.aspen.SuppressDialogs = 1
            self.tree = self.aspen.Tree
            print(f"Aspen Plus 连接成功")
            return True
        except Exception as e:
            print(f"初始化失败: {e}")
            self.disconnect()
            raise

    def disconnect(self):
        if self.aspen:
            try:
                self.aspen.Close()
                self.aspen.Quit()
            except:
                pass
        pythoncom.CoUninitialize()

    def get_tree(self):
        return self.tree
