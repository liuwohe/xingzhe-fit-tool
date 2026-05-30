import os
import logging
import tempfile

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QTextEdit, QGroupBox, QCheckBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from core.xingzhe_client import XingzheClient, RateLimitError
from core.onelap_client import OneLapClient
from core.models import FileType, WorkoutInfo

logger = logging.getLogger(__name__)


class AutoSyncThread(QThread):
    progress = Signal(str)
    step_progress = Signal(int, int)
    done = Signal(int, int, int)  # success, fail, skipped

    def __init__(self, xz_client: XingzheClient, ol_client: OneLapClient,
                 convert_gpx: bool, temp_dir: str):
        super().__init__()
        self.xz_client = xz_client
        self.ol_client = ol_client
        self.convert_gpx = convert_gpx
        self.temp_dir = temp_dir

    def run(self):
        success = 0
        fail = 0
        skipped = 0

        # Step 1: Fetch all workouts
        self.progress.emit("正在从行者获取运动列表...")
        try:
            workouts = self.xz_client.get_all_workouts(
                progress_callback=lambda cur, total: self.step_progress.emit(cur, 0)
            )
        except Exception as e:
            self.progress.emit(f"获取运动列表失败: {e}")
            self.done.emit(0, 0, 0)
            return

        total = len(workouts)
        self.progress.emit(f"获取到 {total} 条运动记录，开始处理...")

        # Step 2: Download and upload each workout
        for i, w in enumerate(workouts):
            self.step_progress.emit(i + 1, total)
            self.progress.emit(f"[{i + 1}/{total}] 处理: {w.title} ({w.date_str})")

            # Download
            ok, msg, file_type = self.xz_client.download_workout(
                w, self.temp_dir, self.convert_gpx
            )
            if not ok:
                self.progress.emit(f"  下载失败: {msg}")
                fail += 1
                continue

            # Find downloaded file
            fit_path = self._find_file(w, file_type)
            if not fit_path:
                self.progress.emit("  未找到下载文件")
                fail += 1
                continue

            # Upload
            ok2, msg2 = self.ol_client.upload_fit(fit_path)
            if ok2:
                self.progress.emit(f"  上传成功")
                success += 1
            else:
                self.progress.emit(f"  上传失败: {msg2}")
                fail += 1

            # Cleanup
            try:
                os.remove(fit_path)
            except OSError:
                pass

        self.progress.emit(f"全部完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}")
        self.done.emit(success, fail, skipped)

    def _find_file(self, workout: WorkoutInfo, file_type: FileType) -> str | None:
        date_prefix = workout.date.strftime("%Y%m%d") if workout.date else str(workout.id)
        safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in workout.title)[:50]
        base_name = f"{date_prefix}_{safe_title}"
        ext = ".fit" if file_type == FileType.FIT else ".gpx"
        path = os.path.join(self.temp_dir, f"{base_name}{ext}")
        if os.path.exists(path):
            return path
        # Fallback: find any file with workout id in name
        for f in os.listdir(self.temp_dir):
            if f.endswith(ext):
                return os.path.join(self.temp_dir, f)
        return None


class AutoSyncTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.xz_client = None
        self.ol_client = None
        self.sync_thread = None
        self.temp_dir = tempfile.mkdtemp(prefix="fittool_")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Token section
        token_group = QGroupBox("账号配置")
        token_layout = QVBoxLayout(token_group)

        # Xingzhe token
        xz_row = QHBoxLayout()
        xz_row.addWidget(QLabel("行者 Token:"))
        self.xz_token_input = QLineEdit()
        self.xz_token_input.setPlaceholderText("粘贴行者 Token...")
        self.xz_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        xz_row.addWidget(self.xz_token_input)
        self.xz_show_cb = QCheckBox("显示")
        self.xz_show_cb.toggled.connect(
            lambda checked: self.xz_token_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        xz_row.addWidget(self.xz_show_cb)
        token_layout.addLayout(xz_row)

        # OneLap token
        ol_row = QHBoxLayout()
        ol_row.addWidget(QLabel("顽鹿 Token:"))
        self.ol_token_input = QLineEdit()
        self.ol_token_input.setPlaceholderText("粘贴顽鹿 Token...")
        self.ol_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        ol_row.addWidget(self.ol_token_input)
        self.ol_show_cb = QCheckBox("显示")
        self.ol_show_cb.toggled.connect(
            lambda checked: self.ol_token_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        ol_row.addWidget(self.ol_show_cb)
        token_layout.addLayout(ol_row)

        # Test connection buttons
        test_row = QHBoxLayout()
        self.test_xz_btn = QPushButton("测试行者")
        self.test_xz_btn.clicked.connect(self._test_xingzhe)
        test_row.addWidget(self.test_xz_btn)

        self.test_ol_btn = QPushButton("测试顽鹿")
        self.test_ol_btn.clicked.connect(self._test_onelap)
        test_row.addWidget(self.test_ol_btn)

        self.conn_status = QLabel("")
        self.conn_status.setObjectName("statusLabel")
        test_row.addWidget(self.conn_status)
        test_row.addStretch()
        token_layout.addLayout(test_row)

        layout.addWidget(token_group)

        # Options
        opt_row = QHBoxLayout()
        self.convert_cb = QCheckBox("GPX 自动转换为 FIT")
        self.convert_cb.setChecked(True)
        opt_row.addWidget(self.convert_cb)
        opt_row.addStretch()
        layout.addLayout(opt_row)

        # Sync button + progress
        sync_row = QHBoxLayout()
        self.sync_btn = QPushButton("开始自动同步")
        self.sync_btn.setObjectName("primaryBtn")
        self.sync_btn.clicked.connect(self._start_sync)
        sync_row.addWidget(self.sync_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        sync_row.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        sync_row.addWidget(self.status_label)
        layout.addLayout(sync_row)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def _log(self, msg: str):
        self.log_text.append(msg)
        logger.info(msg)

    def _test_xingzhe(self):
        token = self.xz_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请输入行者 Token")
            return
        self.test_xz_btn.setEnabled(False)
        self.test_xz_btn.setText("测试中...")

        class T(QThread):
            done = Signal(bool, str)
            def __init__(self, c):
                super().__init__()
                self.c = c
            def run(self):
                ok, msg = self.c.test_connection()
                self.done.emit(ok, msg)

        self._xz_test = T(XingzheClient(token))
        self._xz_test.done.connect(self._on_xz_test)
        self._xz_test.start()

    def _on_xz_test(self, ok, msg):
        self.test_xz_btn.setEnabled(True)
        self.test_xz_btn.setText("测试行者")
        if ok:
            self.xz_client = XingzheClient(self.xz_token_input.text().strip())
            self.test_xz_btn.setStyleSheet("color: #a6e3a1;")
            self.test_xz_btn.setText("行者OK")
            self._log("行者连接成功")
        else:
            self.test_xz_btn.setStyleSheet("")
            self._log(f"行者连接失败: {msg}")
            QMessageBox.warning(self, "连接失败", f"行者: {msg}")
        self._update_conn_status()

    def _test_onelap(self):
        token = self.ol_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "提示", "请输入顽鹿 Token")
            return
        self.test_ol_btn.setEnabled(False)
        self.test_ol_btn.setText("测试中...")

        class T(QThread):
            done = Signal(bool, str)
            def __init__(self, c):
                super().__init__()
                self.c = c
            def run(self):
                ok, msg = self.c.test_connection()
                self.done.emit(ok, msg)

        self._ol_test = T(OneLapClient(token))
        self._ol_test.done.connect(self._on_ol_test)
        self._ol_test.start()

    def _on_ol_test(self, ok, msg):
        self.test_ol_btn.setEnabled(True)
        self.test_ol_btn.setText("测试顽鹿")
        if ok:
            self.ol_client = OneLapClient(self.ol_token_input.text().strip())
            self.test_ol_btn.setStyleSheet("color: #a6e3a1;")
            self.test_ol_btn.setText("顽鹿OK")
            self._log("顽鹿连接成功")
        else:
            self.test_ol_btn.setStyleSheet("")
            self._log(f"顽鹿连接失败: {msg}")
            QMessageBox.warning(self, "连接失败", f"顽鹿: {msg}")
        self._update_conn_status()

    def _update_conn_status(self):
        xz_ok = self.xz_client is not None
        ol_ok = self.ol_client is not None
        if xz_ok and ol_ok:
            self.conn_status.setText("两个平台均已连接，可以开始同步")
            self.conn_status.setStyleSheet("color: #a6e3a1;")
            self.sync_btn.setEnabled(True)
        elif xz_ok:
            self.conn_status.setText("行者已连接，顽鹿未连接")
            self.conn_status.setStyleSheet("color: #f9e2af;")
            self.sync_btn.setEnabled(False)
        elif ol_ok:
            self.conn_status.setText("顽鹿已连接，行者未连接")
            self.conn_status.setStyleSheet("color: #f9e2af;")
            self.sync_btn.setEnabled(False)
        else:
            self.conn_status.setText("未连接")
            self.conn_status.setStyleSheet("")
            self.sync_btn.setEnabled(False)

    def _start_sync(self):
        if not self.xz_client or not self.ol_client:
            QMessageBox.warning(self, "提示", "请先测试两个平台的连接")
            return

        self.sync_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("同步中...")
        self._log("开始自动同步: 行者 → 顽鹿")

        self.sync_thread = AutoSyncThread(
            self.xz_client, self.ol_client,
            self.convert_cb.isChecked(), self.temp_dir,
        )
        self.sync_thread.progress.connect(self._on_sync_log)
        self.sync_thread.step_progress.connect(self._on_sync_step)
        self.sync_thread.done.connect(self._on_sync_done)
        self.sync_thread.start()

    def _on_sync_log(self, msg: str):
        self._log(msg)

    def _on_sync_step(self, current: int, total: int):
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.status_label.setText(f"处理中 {current}/{total}")
        else:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText(f"获取列表中... 已获取 {current} 条")

    def _on_sync_done(self, success: int, fail: int, skipped: int):
        self.sync_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}")
        self._log(f"同步完成: 成功 {success}, 失败 {fail}, 跳过 {skipped}")

    def set_tokens(self, xz_token: str, ol_token: str):
        if xz_token:
            self.xz_token_input.setText(xz_token)
            self.xz_client = XingzheClient(xz_token)
            self.test_xz_btn.setStyleSheet("color: #a6e3a1;")
            self.test_xz_btn.setText("行者OK")
        if ol_token:
            self.ol_token_input.setText(ol_token)
            self.ol_client = OneLapClient(ol_token)
            self.test_ol_btn.setStyleSheet("color: #a6e3a1;")
            self.test_ol_btn.setText("顽鹿OK")
        self._update_conn_status()
