import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QProgressBar, QFileDialog, QTextEdit, QGroupBox,
    QAbstractItemView, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.onelap_client import OneLapClient

logger = logging.getLogger(__name__)


class UploadThread(QThread):
    progress = Signal(int, int)
    single_done = Signal(int, bool, str)
    finished = Signal(int, int)

    def __init__(self, client: OneLapClient, files: list[str]):
        super().__init__()
        self.client = client
        self.files = files

    def run(self):
        success = 0
        fail = 0
        for i, f in enumerate(self.files):
            ok, msg = self.client.upload_fit(f)
            self.single_done.emit(i, ok, msg)
            self.progress.emit(i + 1, len(self.files))
            if ok:
                success += 1
            else:
                fail += 1
        self.finished.emit(success, fail)


class OneLapTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = None
        self._upload_thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Token section
        token_group = QGroupBox("顽鹿账号 Token")
        token_layout = QVBoxLayout(token_group)

        hint = QLabel("在浏览器登录顽鹿后，打开 DevTools (F12) → Application → Local Storage → 复制 Token 值")
        hint.setObjectName("statusLabel")
        hint.setWordWrap(True)
        token_layout.addWidget(hint)

        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("粘贴顽鹿 Token...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        token_row.addWidget(self.token_input)

        self.connect_btn = QPushButton("连接测试")
        self.connect_btn.setObjectName("primaryBtn")
        self.connect_btn.clicked.connect(self._test_connection)

        self.token_input.textChanged.connect(self._on_token_changed)

        token_row.addWidget(self.connect_btn)

        self.show_token_cb = QCheckBox("显示")
        self.show_token_cb.toggled.connect(
            lambda checked: self.token_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        token_row.addWidget(self.show_token_cb)
        token_layout.addLayout(token_row)
        layout.addWidget(token_group)

        # File selection
        file_group = QGroupBox("选择 FIT 文件")
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self.file_list_label = QLabel("已选择 0 个文件")
        file_row.addWidget(self.file_list_label)

        add_btn = QPushButton("添加文件")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_files)
        file_row.addWidget(add_btn)

        add_dir_btn = QPushButton("添加目录")
        add_dir_btn.clicked.connect(self._add_dir)
        file_row.addWidget(add_dir_btn)

        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self._clear_files)
        file_row.addWidget(clear_btn)
        file_layout.addLayout(file_row)

        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["选择", "文件名", "大小"])
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.file_table.setColumnWidth(0, 50)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.verticalHeader().setVisible(False)
        file_layout.addWidget(self.file_table)

        select_row = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all)
        select_row.addWidget(self.select_all_btn)
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        select_row.addWidget(self.deselect_all_btn)
        select_row.addStretch()
        file_layout.addLayout(select_row)
        layout.addWidget(file_group)

        # Upload section
        upload_row = QHBoxLayout()
        self.upload_btn = QPushButton("上传选中文件到顽鹿")
        self.upload_btn.setObjectName("primaryBtn")
        self.upload_btn.clicked.connect(self._upload_files)
        self.upload_btn.setEnabled(False)
        upload_row.addWidget(self.upload_btn)

        self.upload_progress = QProgressBar()
        self.upload_progress.setVisible(False)
        upload_row.addWidget(self.upload_progress)

        self.upload_status = QLabel("")
        self.upload_status.setObjectName("statusLabel")
        upload_row.addWidget(self.upload_status)
        layout.addLayout(upload_row)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.files: list[str] = []

    def _log(self, msg: str):
        self.log_text.append(msg)
        logger.info(msg)

    def _test_connection(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请输入 Token")
            return

        self.client = OneLapClient(token)
        self.connect_btn.setText("测试中...")
        self.connect_btn.setEnabled(False)

        class TestThread(QThread):
            done = Signal(bool, str)

            def __init__(self, c):
                super().__init__()
                self.c = c

            def run(self):
                ok, msg = self.c.test_connection()
                self.done.emit(ok, msg)

        self._test_thread = TestThread(self.client)
        self._test_thread.done.connect(self._on_test_result)
        self._test_thread.start()

    def _on_test_result(self, ok: bool, msg: str):
        self.connect_btn.setText("连接测试")
        self.connect_btn.setEnabled(True)
        if ok:
            self.upload_btn.setEnabled(True)
            self._log("顽鹿连接成功")
            self.connect_btn.setText("已连接")
            self.connect_btn.setStyleSheet("color: #a6e3a1;")
        else:
            self._log(f"顽鹿连接失败: {msg}")
            QMessageBox.warning(self, "连接失败", msg)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 FIT 文件", "", "FIT 文件 (*.fit);;所有文件 (*)")
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh_file_table()

    def _add_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择包含 FIT 文件的目录")
        if dir_path:
            for f in os.listdir(dir_path):
                if f.lower().endswith(".fit"):
                    full = os.path.join(dir_path, f)
                    if full not in self.files:
                        self.files.append(full)
            self._refresh_file_table()

    def _clear_files(self):
        self.files.clear()
        self._refresh_file_table()

    def _refresh_file_table(self):
        self.file_table.setRowCount(len(self.files))
        for i, f in enumerate(self.files):
            cb = QCheckBox()
            cb.setChecked(True)
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.file_table.setCellWidget(i, 0, cb_widget)

            self.file_table.setItem(i, 1, QTableWidgetItem(os.path.basename(f)))

            try:
                size_kb = os.path.getsize(f) / 1024
                self.file_table.setItem(i, 2, QTableWidgetItem(f"{size_kb:.1f} KB"))
            except OSError:
                self.file_table.setItem(i, 2, QTableWidgetItem("未知"))

        self.file_list_label.setText(f"已选择 {len(self.files)} 个文件")

    def _get_selected_files(self) -> list[str]:
        selected = []
        for i in range(self.file_table.rowCount()):
            cb_widget = self.file_table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected.append(self.files[i])
        return selected

    def _select_all(self):
        for i in range(self.file_table.rowCount()):
            cb_widget = self.file_table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def _deselect_all(self):
        for i in range(self.file_table.rowCount()):
            cb_widget = self.file_table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def _upload_files(self):
        selected = self._get_selected_files()
        if not selected:
            QMessageBox.warning(self, "提示", "请选择要上传的文件")
            return

        if not self.client:
            QMessageBox.warning(self, "提示", "请先连接顽鹿账号")
            return

        self.upload_btn.setEnabled(False)
        self.upload_progress.setVisible(True)
        self.upload_progress.setRange(0, len(selected))
        self.upload_progress.setValue(0)
        self.upload_status.setText("上传中...")
        self._log(f"开始上传 {len(selected)} 个文件到顽鹿...")

        self._upload_thread = UploadThread(self.client, selected)
        self._upload_thread.progress.connect(self._on_upload_progress)
        self._upload_thread.single_done.connect(self._on_upload_single)
        self._upload_thread.finished.connect(self._on_upload_done)
        self._upload_thread.start()

    def _on_upload_progress(self, current: int, total: int):
        self.upload_progress.setValue(current)
        self.upload_status.setText(f"上传中 {current}/{total}")

    def _on_upload_single(self, index: int, ok: bool, msg: str):
        status = "成功" if ok else "失败"
        self._log(f"  [{index + 1}] {status}: {msg}")

    def _on_upload_done(self, success: int, fail: int):
        self.upload_btn.setEnabled(True)
        self.upload_progress.setVisible(False)
        self.upload_status.setText(f"完成: 成功 {success}, 失败 {fail}")
        self._log(f"上传完成: 成功 {success}, 失败 {fail}")

    def _on_token_changed(self):
        self.upload_btn.setEnabled(False)
        self.connect_btn.setText("连接测试")
        self.connect_btn.setEnabled(True)

    def get_token(self) -> str:
        return self.token_input.text().strip()