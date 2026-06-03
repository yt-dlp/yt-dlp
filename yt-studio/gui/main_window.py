from PySide6.QtCore import QTimer, QTime, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.history import HistoryStore
from gui.download_tab import DownloadTab
from gui.history_tab import HistoryTab
from gui.queue_tab import QueueTab
from gui.retro_style import APP_QSS
from gui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YT-Studio")
        self.resize(1180, 720)
        self.setStyleSheet(APP_QSS)

        self.history_store = HistoryStore()
        self.queue_tab = QueueTab()
        self.settings_tab = SettingsTab(self.history_store)
        self.history_tab = HistoryTab(self.history_store)
        self.download_tab = DownloadTab(self.history_store, self.history_tab.refresh, self.queue_tab.add_job)

        self.status_left = QLabel("DOWNLOAD MODE")
        self.status_center = QLabel("YT-STUDIO v1.0")
        self.status_right = QLabel("")
        self.nav_buttons = []
        self.screen_stack = QStackedWidget()

        self._build_shell()
        self._wire_clock()

    def _build_shell(self):
        root = QWidget()
        root.setObjectName("retro-root")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._titlebar())
        root_layout.addWidget(self._menubar())

        body = QFrame()
        body.setObjectName("content-frame")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._sidebar())

        self.screen_stack.addWidget(self.download_tab)
        self.screen_stack.addWidget(self.queue_tab)
        self.screen_stack.addWidget(self.history_tab)
        self.screen_stack.addWidget(self.settings_tab)
        body_layout.addWidget(self.screen_stack, 1)
        root_layout.addWidget(body, 1)
        root_layout.addWidget(self._statusbar())

        self._activate_nav(0)

    def _titlebar(self):
        titlebar = QWidget()
        titlebar.setObjectName("titlebar")
        layout = QHBoxLayout(titlebar)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(3)
        title = QLabel("YT-STUDIO v1.0  [DOWNLOAD MANAGER]")
        title.setObjectName("title-text")
        layout.addWidget(title, 1)
        for label in ("_", "^", "X"):
            button = QPushButton(label)
            button.setObjectName("window-button")
            layout.addWidget(button)
        return titlebar

    def _menubar(self):
        menubar = QWidget()
        menubar.setObjectName("menubar")
        layout = QHBoxLayout(menubar)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)
        for text in ("File", "Edit", "View", "Tools", "Help"):
            label = QLabel(text)
            label.setObjectName("menu-item")
            layout.addWidget(label)
        layout.addStretch(1)
        return menubar

    def _sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(110)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        for index, (name, text) in enumerate(
            (
                ("nav-download", "DOWNLOAD"),
                ("nav-queue", "QUEUE"),
                ("nav-history", "HISTORY"),
                ("nav-config", "CONFIG"),
            )
        ):
            button = QPushButton(text)
            button.setObjectName(name)
            button.setProperty("active", False)
            button.clicked.connect(lambda _checked=False, i=index: self._activate_nav(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        diagnostics = QLabel("MEM: 640K OK\nVER: 2026.03\nFFMPEG: OK")
        diagnostics.setObjectName("side-diagnostics")
        diagnostics.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        layout.addWidget(diagnostics)
        return sidebar

    def _statusbar(self):
        statusbar = QWidget()
        statusbar.setObjectName("statusbar")
        layout = QHBoxLayout(statusbar)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.addWidget(self.status_left)
        self.status_center.setAlignment(Qt.AlignCenter)
        self.status_center.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.status_center)
        self.status_right.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_right)
        return statusbar

    def _wire_clock(self):
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        self._tick()

    def _tick(self):
        self.status_right.setText(QTime.currentTime().toString("HH:mm:ss"))

    def _activate_nav(self, index: int):
        labels = ("DOWNLOAD MODE", "QUEUE MANAGER", "HISTORY LOG", "CONFIGURATION")
        self.screen_stack.setCurrentIndex(index)
        self.status_left.setText(labels[index])
        for button_index, button in enumerate(self.nav_buttons):
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
