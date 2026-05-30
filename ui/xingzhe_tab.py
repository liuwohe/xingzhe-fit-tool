import os
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QProgressBar, QFileDialog, QTextEdit, QGroupBox,
    QAbstractItemView, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.models import WorkoutInfo, FileType
from core.xingzhe_client import XingzheClient

logger = logging.getLogger(__name__)


class FetchWorkoutsThread(QThread):
    progress = Signal(int, int)
    finished = Signal(list, str)

    def __init__(self, client: XingzheClient):
        super().__init__()
        self.client = client

    def run(self):
        try:
            workouts = self.client.get_all_workouts(
                progress_callback=lambda cur, total: self.progress.emit(cur, total)
            )
            self.finished.emit(workouts, "")
        except Exception as e:
            self.finished.emit([], str(e))


class ExportWorkoutsThread(QThread):
    progress = Signal(int, int)
    single_done = Signal(int, bool, str)
    finished = Signal(int, int)

    def __init__(self, client: XingzheClient, workouts: list[WorkoutInfo],
                 save_dir: str, convert_gpx: bool):
        super().__init__()
        self.client = client
        self.workouts = workouts
        self.save_dir = save_dir
        self.convert_gpx = convert_gpx

    def run(self):
        success = 0
        fail = 0
        for i, w in enumerate(self.workouts):
            ok, msg, _ = self.client.download_workout(w, self.save_dir, self.convert_gpx)
            self.single_done.emit(i, ok, msg)
            self.progress.emit(i + 1, len(self.workouts))
            if ok:
                success += 1
            else:
                fail += 1
        self.finished.emit(success, fail)


class XingzheTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = None
        self.workouts: list[WorkoutInfo] = []
        self.fetch_thread = None
        self.export_thread = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Token section
        token_group = QGroupBox("行者账号 Token")
        token_layout = QVBoxLayout(token_group)

        hint = QLabel("在浏览器登录行者后，打开 DevTools (F12) → Application → Local Storage → 复制 Token 值")
        hint.setObjectName("statusLabel")
        hint.setWordWrap(True)
        token_layout.addWidget(hint)

        token_row = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("粘贴行者 Token...")
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

        # Fetch section
        fetch_row = QHBoxLayout()
        self.fetch_btn = QPushButton("获取运动列表")
        self.fetch_btn.setObjectName("primaryBtn")
        self.fetch_btn.clicked.connect(self._fetch_workouts)
        self.fetch_btn.setEnabled(False)
        fetch_row.addWidget(self.fetch_btn)

        self.fetch_progress = QProgressBar()
        self.fetch_progress.setVisible(False)
        fetch_row.addWidget(self.fetch_progress)

        self.fetch_status = QLabel("")
        self.fetch_status.setObjectName("statusLabel")
        fetch_row.addWidget(self.fetch_status)
        fetch_row.addStretch()
        layout.addLayout(fetch_row)

        # Workout table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["选择", "日期", "标题", "距离", "时长", "均速", "类型", "格式"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Export section
        export_group = QGroupBox("导出设置")
        export_layout = QVBoxLayout(export_group)

        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("保存目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("选择导出文件保存目录...")
        default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        self.dir_input.setText(default_dir)
        dir_row.addWidget(self.dir_input)
        dir_btn = QPushButton("浏览")
        dir_btn.clicked.connect(self._choose_dir)
        dir_row.addWidget(dir_btn)
        export_layout.addLayout(dir_row)

        options_row = QHBoxLayout()
        self.convert_cb = QCheckBox("GPX 自动转换为 FIT")
        self.convert_cb.setChecked(True)
        options_row.addWidget(self.convert_cb)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self._select_all)
        options_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        options_row.addWidget(self.deselect_all_btn)
        options_row.addStretch()
        export_layout.addLayout(options_row)

        export_btn_row = QHBoxLayout()
        self.export_btn = QPushButton("导出选中记录")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.clicked.connect(self._export_workouts)
        self.export_btn.setEnabled(False)
        export_btn_row.addWidget(self.export_btn)

        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        export_btn_row.addWidget(self.export_progress)

        self.export_status = QLabel("")
        self.export_status.setObjectName("statusLabel")
        export_btn_row.addWidget(self.export_status)
        export_layout.addLayout(export_btn_row)
        layout.addWidget(export_group)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def _log(self, msg: str):
        self.log_text.append(msg)
        logger.info(msg)

    def _test_connection(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请输入 Token")
            return

        self.client = XingzheClient(token)
        self.connect_btn.setText("测试中...")
        self.connect_btn.setEnabled(False)

        from PySide6.QtCore import QThread

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
            self.fetch_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self._log(f"行者连接成功")
            self.connect_btn.setText("已连接")
            self.connect_btn.setStyleSheet("color: #a6e3a1;")
        else:
            self._log(f"行者连接失败: {msg}")
            QMessageBox.warning(self, "连接失败", msg)

    def _fetch_workouts(self):
        if not self.client:
            return
        self.fetch_btn.setEnabled(False)
        self.fetch_progress.setVisible(True)
        self.fetch_progress.setRange(0, 0)
        self.fetch_status.setText("获取中...")
        self._log("开始获取运动列表...")

        self.fetch_thread = FetchWorkoutsThread(self.client)
        self.fetch_thread.progress.connect(self._on_fetch_progress)
        self.fetch_thread.finished.connect(self._on_fetch_done)
        self.fetch_thread.start()

    def _on_fetch_progress(self, current: int, total: int):
        if total > 0:
            self.fetch_progress.setRange(0, total)
            self.fetch_progress.setValue(current)
            self.fetch_status.setText(f"已获取 {current}/{total} 条记录")
        else:
            self.fetch_progress.setRange(0, 0)
            self.fetch_status.setText(f"已获取 {current} 条记录...")

    def _on_fetch_done(self, workouts: list, error: str):
        self.fetch_btn.setEnabled(True)
        self.fetch_progress.setVisible(False)

        if error:
            self.fetch_status.setText(f"获取失败: {error}")
            self._log(f"获取运动列表失败: {error}")
            return

        self.workouts = workouts
        self.fetch_status.setText(f"共 {len(workouts)} 条记录")
        self.export_btn.setEnabled(True)
        self._log(f"获取到 {len(workouts)} 条运动记录")
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(len(self.workouts))
        for i, w in enumerate(self.workouts):
            cb = QCheckBox()
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, cb_widget)

            self.table.setItem(i, 1, QTableWidgetItem(w.date_str))
            self.table.setItem(i, 2, QTableWidgetItem(w.title))
            self.table.setItem(i, 3, QTableWidgetItem(w.distance_str))
            self.table.setItem(i, 4, QTableWidgetItem(w.duration_str))
            self.table.setItem(i, 5, QTableWidgetItem(w.avg_speed_str))
            self.table.setItem(i, 6, QTableWidgetItem(w.sport_type.display))
            self.table.setItem(i, 7, QTableWidgetItem(w.file_type.value))

    def _get_selected_workouts(self) -> list[WorkoutInfo]:
        selected = []
        for i in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb and cb.isChecked():
                    selected.append(self.workouts[i])
        return selected

    def _select_all(self):
        for i in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(True)

    def _deselect_all(self):
        for i in range(self.table.rowCount()):
            cb_widget = self.table.cellWidget(i, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.setChecked(False)

    def _choose_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self.dir_input.setText(dir_path)

    def _export_workouts(self):
        selected = self._get_selected_workouts()
        if not selected:
            QMessageBox.warning(self, "提示", "请选择要导出的运动记录")
            return

        save_dir = self.dir_input.text().strip()
        if not save_dir or not os.path.isdir(save_dir):
            QMessageBox.warning(self, "提示", "请选择有效的保存目录")
            return

        self.export_btn.setEnabled(False)
        self.export_progress.setVisible(True)
        self.export_progress.setRange(0, len(selected))
        self.export_progress.setValue(0)
        self.export_status.setText("导出中...")
        self._log(f"开始导出 {len(selected)} 条记录...")

        self.export_thread = ExportWorkoutsThread(
            self.client, selected, save_dir, self.convert_cb.isChecked()
        )
        self.export_thread.progress.connect(self._on_export_progress)
        self.export_thread.single_done.connect(self._on_export_single)
        self.export_thread.finished.connect(self._on_export_done)
        self.export_thread.start()

    def _on_export_progress(self, current: int, total: int):
        self.export_progress.setValue(current)
        self.export_status.setText(f"导出中 {current}/{total}")

    def _on_export_single(self, index: int, ok: bool, msg: str):
        status = "成功" if ok else "失败"
        self._log(f"  [{index + 1}] {status}: {msg}")

    def _on_export_done(self, success: int, fail: int):
        self.export_btn.setEnabled(True)
        self.export_progress.setVisible(False)
        self.export_status.setText(f"完成: 成功 {success}, 失败 {fail}")
        self._log(f"导出完成: 成功 {success}, 失败 {fail}")

    def _on_token_changed(self):
        self.fetch_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.connect_btn.setText("连接测试")
        self.connect_btn.setEnabled(True)

    def get_token(self) -> str:
        return self.token_input.text().strip()
