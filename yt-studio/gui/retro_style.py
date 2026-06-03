APP_QSS = """
* {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 11px;
}
QMainWindow, QWidget#retro-root {
    background: #0a0e0a;
    color: #39ff14;
}
QWidget#titlebar {
    background: #1a8c00;
    color: #000000;
}
QLabel#title-text {
    color: #000000;
    font-size: 13px;
    font-weight: 700;
}
QPushButton#window-button {
    min-width: 16px;
    max-width: 16px;
    min-height: 14px;
    max-height: 14px;
    padding: 0;
    background: #39ff14;
    color: #000000;
    border: 1px solid #0d4d00;
}
QWidget#menubar, QWidget#statusbar {
    background: #0f140f;
    border-top: 1px solid #2a502a;
    border-bottom: 1px solid #2a502a;
}
QToolButton#menu-item {
    background: transparent;
    border: 0;
    color: #39ff14;
    padding: 2px 10px;
    font-weight: 400;
}
QToolButton#menu-item:hover,
QToolButton#menu-item:pressed {
    background: #1a8c00;
    color: #000000;
}
QToolButton#menu-item::menu-indicator {
    image: none;
}
QMenu#retro-menu {
    background: #0f140f;
    color: #39ff14;
    border: 1px solid #1a8c00;
}
QMenu#retro-menu::item {
    padding: 4px 28px 4px 10px;
}
QMenu#retro-menu::item:selected {
    background: #1a8c00;
    color: #000000;
}
QMenu#retro-menu::separator {
    height: 1px;
    background: #2a502a;
    margin: 3px 6px;
}
QWidget#sidebar {
    background: #0f140f;
    border-right: 1px solid #2a502a;
}
QPushButton#nav-download,
QPushButton#nav-queue,
QPushButton#nav-history,
QPushButton#nav-config {
    background: transparent;
    color: #39ff14;
    border: 0;
    text-align: left;
    padding: 8px 12px;
    font-weight: 700;
}
QPushButton[active="true"] {
    background: #1a8c00;
    color: #000000;
}
QLabel#side-diagnostics {
    color: #0d4d00;
    padding: 8px;
}
QFrame#content-frame {
    background: #0f140f;
}
QGroupBox {
    border: 1px solid #2a502a;
    margin-top: 14px;
    padding: 9px;
    color: #ffb800;
    background: #141a14;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QLabel {
    color: #39ff14;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background: #0a0e0a;
    color: #39ff14;
    border: 1px solid #0d4d00;
    selection-background-color: #1a8c00;
    selection-color: #000000;
    padding: 3px 6px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #1a8c00;
}
QCheckBox {
    color: #39ff14;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #1a8c00;
    background: #0a0e0a;
}
QCheckBox::indicator:checked {
    background: #39ff14;
}
QPushButton {
    background: #141a14;
    color: #39ff14;
    border: 1px solid #1a8c00;
    padding: 5px 12px;
    font-weight: 700;
}
QPushButton:hover {
    background: #1f2b1f;
}
QPushButton#primary-button {
    background: #39ff14;
    color: #000000;
}
QPushButton#primary-button:hover {
    background: #ffb800;
}
QProgressBar {
    border: 1px solid #1a8c00;
    background: #0a0e0a;
    color: #39ff14;
    text-align: left;
    height: 18px;
}
QProgressBar::chunk {
    background: #39ff14;
    width: 8px;
    margin: 1px;
}
QTableWidget {
    background: #0a0e0a;
    color: #39ff14;
    gridline-color: #1e3a1e;
    border: 1px solid #2a502a;
}
QHeaderView::section {
    background: #141a14;
    color: #ffb800;
    border: 1px solid #2a502a;
    padding: 3px;
}
QScrollBar:vertical {
    background: #0a0e0a;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #0d4d00;
    border: 1px solid #1a8c00;
}
"""


def bracket(text: str) -> str:
    return f"[ {text.upper()} ]"
