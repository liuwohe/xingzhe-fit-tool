from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont


DARK_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    background-color: #1e1e2e;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #45475a;
    color: #cba6f7;
}
QTabBar::tab:hover:!selected {
    background-color: #3b3b50;
}
QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    padding: 6px 16px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton:pressed {
    background-color: #6c7086;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
}
QPushButton#primaryBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #74c7ec;
}
QPushButton#dangerBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
}
QPushButton#dangerBtn:hover {
    background-color: #eba0ac;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 6px 10px;
    border-radius: 4px;
}
QLineEdit:focus {
    border-color: #89b4fa;
}
QTableWidget {
    background-color: #181825;
    alternate-background-color: #1e1e2e;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
}
QTableWidget::item {
    padding: 4px;
}
QTableWidget::item:selected {
    background-color: #45475a;
    color: #cba6f7;
}
QHeaderView::section {
    background-color: #313244;
    color: #cdd6f4;
    padding: 6px;
    border: 1px solid #45475a;
    font-weight: bold;
}
QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #585b70;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QProgressBar {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}
QLabel#statusLabel {
    color: #a6adc8;
    font-size: 12px;
}
QLabel#successLabel {
    color: #a6e3a1;
}
QLabel#errorLabel {
    color: #f38ba8;
}
QScrollArea {
    border: none;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #cba6f7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
}
QTextEdit {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
}
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    padding: 4px 8px;
    border-radius: 4px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
}
"""
