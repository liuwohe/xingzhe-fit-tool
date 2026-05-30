import os

from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from ui.auto_sync_tab import AutoSyncTab
from ui.xingzhe_tab import XingzheTab
from ui.onelap_tab import OneLapTab
from ui.settings_tab import SettingsTab
from ui.styles import DARK_STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FIT 运动数据工具 - 行者导出 / 顽鹿导入")
        self.setMinimumSize(900, 650)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 8)

        # Tabs
        self.tabs = QTabWidget()
        self.auto_sync_tab = AutoSyncTab()
        self.xingzhe_tab = XingzheTab()
        self.onelap_tab = OneLapTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.auto_sync_tab, "自动同步")
        self.tabs.addTab(self.xingzhe_tab, "行者导出")
        self.tabs.addTab(self.onelap_tab, "顽鹿导入")
        self.tabs.addTab(self.settings_tab, "设置")

        layout.addWidget(self.tabs)

        # Sync settings to tabs on startup
        self._sync_settings()

        # Sync when settings tab is left
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Status bar
        status = QLabel("就绪")
        status.setObjectName("statusLabel")
        self.statusBar().addWidget(status)

    def _sync_settings(self):
        xz_token = self.settings_tab.get_xingzhe_token()
        if xz_token:
            self.xingzhe_tab.token_input.setText(xz_token)

        ol_token = self.settings_tab.get_onelap_token()
        if ol_token:
            self.onelap_tab.token_input.setText(ol_token)

        output_dir = self.settings_tab.get_output_dir()
        if output_dir:
            self.xingzhe_tab.dir_input.setText(output_dir)

        self.auto_sync_tab.set_tokens(xz_token, ol_token)

    def _on_tab_changed(self, index: int):
        if index == 0:
            xz_token = self.settings_tab.get_xingzhe_token()
            if xz_token and not self.xingzhe_tab.token_input.text().strip():
                self.xingzhe_tab.token_input.setText(xz_token)

            output_dir = self.settings_tab.get_output_dir()
            if output_dir and self.xingzhe_tab.dir_input.text().strip() == os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"
            ):
                self.xingzhe_tab.dir_input.setText(output_dir)

        elif index == 1:
            ol_token = self.settings_tab.get_onelap_token()
            if ol_token and not self.onelap_tab.token_input.text().strip():
                self.onelap_tab.token_input.setText(ol_token)