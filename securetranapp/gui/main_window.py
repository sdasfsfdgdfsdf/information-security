
# gui/main_window.py
import threading

from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit,
    QProgressBar, QFrame, QGroupBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QObject, QMetaObject, Q_ARG
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor

class ProgressSignals(QObject):
    update_progress = pyqtSignal(int, str)
    update_log = pyqtSignal(str)
    update_key_status = pyqtSignal(str, str)
    update_server_status = pyqtSignal(str, str)
    update_button_enabled = pyqtSignal(bool)

class CryptoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔐 安全文件传输系统")
        self.setGeometry(100, 100, 900, 650)
        self.setMinimumSize(800, 550)
        
        font = QFont("Microsoft YaHei", 11)
        self.setFont(font)
        
        self.setWindowIcon(QIcon.fromTheme("lock"))
        
        self.signals = ProgressSignals()
        self._connect_signals()
        
        main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        
        self._add_title_section()
        self._add_file_section()
        self._add_key_section()
        self._add_server_section()
        self._add_transfer_section()
        self._add_progress_section()
        self._add_log_section()
        
        main_widget.setLayout(self.main_layout)
        self.setCentralWidget(main_widget)
        
        self._apply_styles()
    
    def _connect_signals(self):
        self.signals.update_progress.connect(self._update_progress_safe)
        self.signals.update_log.connect(self._log_safe)
        self.signals.update_key_status.connect(self._update_key_status_safe)
        self.signals.update_server_status.connect(self._update_server_status_safe)
        self.signals.update_button_enabled.connect(self._update_button_enabled_safe)
    
    def _update_progress_safe(self, progress, message):
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def _log_safe(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"[{timestamp}] {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
    
    def _update_key_status_safe(self, text, style):
        self.key_status.setText(text)
        self.key_status.setStyleSheet(style)
    
    def _update_server_status_safe(self, text, style):
        self.server_status.setText(text)
        self.server_status.setStyleSheet(style)
    
    def _update_button_enabled_safe(self, enabled):
        self.btn_start_server.setEnabled(enabled)
    
    def _add_title_section(self):
        title_label = QLabel("🔐 安全文件传输系统")
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50;")
        
        subtitle_label = QLabel("基于 RSA + AES 混合加密的安全文件传输工具")
        subtitle_label.setFont(QFont("Microsoft YaHei", 12))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #7f8c8d;")
        
        title_layout = QVBoxLayout()
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        title_frame = QFrame()
        title_frame.setLayout(title_layout)
        title_frame.setFrameShape(QFrame.HLine)
        title_frame.setFrameShadow(QFrame.Sunken)
        title_frame.setStyleSheet("border-bottom: 2px solid #3498db; margin-bottom: 10px;")
        
        self.main_layout.addWidget(title_frame)
    
    def _add_file_section(self):
        group_box = QGroupBox("📁 文件选择")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("请选择要传输的文件...")
        self.file_path.setStyleSheet(self._get_line_edit_style())
        
        self.btn_choose = QPushButton("📂 选择文件")
        self.btn_choose.setStyleSheet(self._get_button_style())
        self.btn_choose.clicked.connect(self.choose_file)
        
        layout.addWidget(self.file_path)
        layout.addWidget(self.btn_choose)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _add_key_section(self):
        group_box = QGroupBox("🔑 密钥管理")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.btn_gen_keys = QPushButton("🔐 生成密钥对")
        self.btn_gen_keys.setStyleSheet(self._get_button_style())
        self.btn_gen_keys.clicked.connect(self.generate_keys)
        
        self.key_status = QLabel("状态: 未生成密钥")
        self.key_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        layout.addWidget(self.btn_gen_keys)
        layout.addStretch()
        layout.addWidget(self.key_status)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _add_server_section(self):
        group_box = QGroupBox("🌐 服务器设置")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.btn_start_server = QPushButton("🚀 启动服务器")
        self.btn_start_server.setStyleSheet(self._get_button_style())
        self.btn_start_server.clicked.connect(self.start_server)
        
        ip_label = QLabel("服务器 IP:")
        ip_label.setStyleSheet("color: #34495e;")
        
        self.server_ip = QLineEdit("127.0.0.1")
        self.server_ip.setFixedWidth(150)
        self.server_ip.setStyleSheet(self._get_line_edit_style())
        
        self.btn_connect = QPushButton("🔗 连接服务器")
        self.btn_connect.setStyleSheet(self._get_button_style())
        self.btn_connect.clicked.connect(self.connect_server)
        
        self.server_status = QLabel("状态: 未连接")
        self.server_status.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        layout.addWidget(self.btn_start_server)
        layout.addWidget(ip_label)
        layout.addWidget(self.server_ip)
        layout.addWidget(self.btn_connect)
        layout.addStretch()
        layout.addWidget(self.server_status)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _add_transfer_section(self):
        group_box = QGroupBox("📤 文件传输")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.btn_send = QPushButton("📤 发送文件")
        self.btn_send.setStyleSheet(self._get_button_style(primary=True))
        self.btn_send.setFixedHeight(45)
        self.btn_send.clicked.connect(self.send_file)
        
        layout.addWidget(self.btn_send)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _add_progress_section(self):
        group_box = QGroupBox("📊 传输进度")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.progress_label = QLabel("传输进度: 0%")
        self.progress_label.setStyleSheet("color: #3498db; font-weight: bold;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(self._get_progress_bar_style())
        
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _add_log_section(self):
        group_box = QGroupBox("📝 操作日志")
        group_box.setStyleSheet(self._get_group_box_style())
        
        layout = QVBoxLayout()
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(self._get_text_edit_style())
        self.log_area.setPlaceholderText("操作日志将显示在这里...")
        
        layout.addWidget(self.log_area)
        
        group_box.setLayout(layout)
        self.main_layout.addWidget(group_box)
    
    def _apply_styles(self):
        palette = QPalette()
        palette.setColor(QPalette.Background, QColor(248, 249, 250))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f8f9fa;
            }
        """)
    
    def _get_group_box_style(self):
        return """
            QGroupBox {
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #ffffff;
            }
        """
    
    def _get_button_style(self, primary=False):
        if primary:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3498db, stop:1 #2980b9);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2980b9, stop:1 #2471a3);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2471a3, stop:1 #1f618d);
                }
                QPushButton:disabled {
                    background: #bdc3c7;
                }
            """
        else:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ecf0f1, stop:1 #bdc3c7);
                    color: #2c3e50;
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #bdc3c7, stop:1 #95a5a6);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #95a5a6, stop:1 #7f8c8d);
                }
                QPushButton:disabled {
                    background: #ecf0f1;
                    color: #95a5a6;
                }
            """
    
    def _get_line_edit_style(self):
        return """
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #ffffff;
                color: #2c3e50;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #95a5a6;
            }
        """
    
    def _get_progress_bar_style(self):
        return """
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9);
                border-radius: 6px;
            }
        """
    
    def _get_text_edit_style(self):
        return """
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 10px;
                background-color: #ffffff;
                color: #2c3e50;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }
        """
    
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "所有文件 (*.*)"
        )
        if path:
            self.file_path.setText(path)
            self.log(f"已选择文件: {path}")
    
    def generate_keys(self):
        def worker():
            try:
                from network.core.rsa_utils import generate_keypair, save_key, get_private_key_path, get_public_key_path, get_key_dir
                priv, pub = generate_keypair()
                save_key(priv, get_private_key_path())
                save_key(pub, get_public_key_path(), is_private=False)
                self.signals.update_key_status.emit(
                    "状态: ✅ 密钥已生成",
                    "color: #27ae60; font-weight: bold;"
                )
                self.signals.update_log.emit(f"密钥对已生成，存储位置: {get_key_dir()}")
            except Exception as e:
                self.signals.update_log.emit(f"密钥生成失败: {e}")
        
        threading.Thread(target=worker).start()
    
    def start_server(self):
        def worker():
            try:
                from network.server import FileServer
                self.server = FileServer(progress_callback=self.update_receive_progress)
                self.signals.update_server_status.emit(
                    "状态: 🟢 服务器运行中",
                    "color: #27ae60; font-weight: bold;"
                )
                self.signals.update_button_enabled.emit(False)
                self.signals.update_log.emit("服务器已启动，监听端口 5000")
                self.server.start()
            except Exception as e:
                self.signals.update_log.emit(f"服务器启动失败: {e}")
                self.signals.update_button_enabled.emit(True)
        
        threading.Thread(target=worker).start()
    
    def connect_server(self):
        def worker():
            try:
                from network.client import FileClient
                self.client = FileClient(self.server_ip.text())
                self.signals.update_server_status.emit(
                    f"状态: 🔗 已连接到 {self.server_ip.text()}",
                    "color: #3498db; font-weight: bold;"
                )
                self.signals.update_log.emit(f"已连接到服务器: {self.server_ip.text()}")
            except Exception as e:
                self.signals.update_log.emit(f"连接失败: {e}")
        
        threading.Thread(target=worker).start()
    
    def send_file(self):
        if not hasattr(self, 'client'):
            self.log("❌ 错误：请先连接服务器")
            return
        
        if not self.file_path.text():
            self.log("❌ 错误：请先选择文件")
            return
        
        self.progress_bar.setValue(0)
        self.progress_label.setText("传输进度: 0%")
        
        def worker():
            try:
                self.client.send_file(
                    self.file_path.text(),
                    progress_callback=self.update_send_progress
                )
                self.signals.update_log.emit("✅ 文件发送成功")
                self.signals.update_progress.emit(100, "✅ 传输完成")
            except Exception as e:
                self.signals.update_log.emit(f"❌ 发送失败: {e}")
                self.signals.update_progress.emit(0, "❌ 传输失败")
        
        threading.Thread(target=worker).start()
    
    def update_send_progress(self, progress, message):
        self.signals.update_progress.emit(progress, f"📤 发送进度: {progress}% - {message}")
    
    def update_receive_progress(self, progress, message):
        self.signals.update_progress.emit(progress, f"📥 接收进度: {progress}% - {message}")
    
    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"[{timestamp}] {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
