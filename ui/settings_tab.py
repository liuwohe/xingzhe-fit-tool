import json
import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 行者 Token
        xz_group = QGroupBox("行者平台")
        xz_layout = QVBoxLayout(xz_group)

        xz_hint = QLabel("从浏览器获取 Token: F12 → Application → Local Storage → imxingzhe.com → Token")
        xz_hint.setObjectName("statusLabel")
        xz_hint.setWordWrap(True)
        xz_layout.addWidget(xz_hint)

        xz_row = QHBoxLayout()
        xz_row.addWidget(QLabel("Token:"))
        self.xz_token_input = QLineEdit()
        self.xz_token_input.setPlaceholderText("行者 Token")
        self.xz_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        xz_row.addWidget(self.xz_token_input)
        xz_layout.addLayout(xz_row)
        layout.addWidget(xz_group)

        # 顽鹿 Token
        ol_group = QGroupBox("顽鹿平台")
        ol_layout = QVBoxLayout(ol_group)

        ol_hint = QLabel("从浏览器获取 Token: F12 → Application → Local Storage → otm.onelap.cn → Token")
        ol_hint.setObjectName("statusLabel")
        ol_hint.setWordWrap(True)
        ol_layout.addWidget(ol_hint)

        ol_row = QHBoxLayout()
        ol_row.addWidget(QLabel("Token:"))
        self.ol_token_input = QLineEdit()
        self.ol_token_input.setPlaceholderText("顽鹿 Token")
        self.ol_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        ol_row.addWidget(self.ol_token_input)
        ol_layout.addLayout(ol_row)
        layout.addWidget(ol_group)

        # 导出目录
        dir_group = QGroupBox("默认导出目录")
        dir_layout = QHBoxLayout(dir_group)
        self.dir_input = QLineEdit()
        dir_layout.addWidget(self.dir_input)
        dir_btn = QPushButton("浏览")
        dir_btn.clicked.connect(self._choose_dir)
        dir_layout.addWidget(dir_btn)
        layout.addWidget(dir_group)

        # Save button
        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _choose_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择默认导出目录")
        if dir_path:
            self.dir_input.setText(dir_path)

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            if config.get("xingzhe_token"):
                self.xz_token_input.setText(config["xingzhe_token"])
            if config.get("onelap_token"):
                self.ol_token_input.setText(config["onelap_token"])
            if config.get("output_dir"):
                self.dir_input.setText(config["output_dir"])
        except Exception as e:
            logger.warning("加载配置失败: %s", e)

    def _save_config(self):
        config = {
            "xingzhe_token": self.xz_token_input.text().strip(),
            "onelap_token": self.ol_token_input.text().strip(),
            "output_dir": self.dir_input.text().strip(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "成功", "设置已保存")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def get_xingzhe_token(self) -> str:
        return self.xz_token_input.text().strip()

    def get_onelap_token(self) -> str:
        return self.ol_token_input.text().strip()

    def get_output_dir(self) -> str:
        return self.dir_input.text().strip()