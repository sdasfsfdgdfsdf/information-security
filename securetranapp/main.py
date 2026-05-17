# main.py
import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import CryptoWindow
import os
# 显式导入网络和加密模块
from network.client import FileClient
from network.server import FileServer
from network.file_utils import *
from network.core.rsa_utils import *
from network.core.aes_utils import *
from network.core.signature import *

def resource_path(relative_path):
    """动态获取资源路径（兼容开发环境和打包环境）"""
    if getattr(sys, 'frozen', False):  # 检查是否为打包后的环境
        base_path = sys._MEIPASS      # PyInstaller 临时文件夹路径
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 示例：加载图标
icon_path = resource_path("gui_icon.ico")
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CryptoWindow()
    window.show()
    sys.exit(app.exec_())