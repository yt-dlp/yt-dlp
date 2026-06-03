import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QTime, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
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
        self.download_tab = DownloadTab(
            self.history_store,
            self.history_tab.refresh,
            self.queue_tab.add_job,
            self.queue_tab.update_job,
        )
        self.queue_tab.start_requested.connect(self.download_tab.start_job)
        self.queue_tab.pause_requested.connect(self.download_tab.pause_queue_job)

        self.status_left = QLabel("DOWNLOAD MODE")
        self.status_center = QLabel("YT-STUDIO v1.0")
        self.status_right = QLabel("")
        self.nav_buttons = []
        self.menu_buttons = {}
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
        for label, handler in (
            ("_", self.showMinimized),
            ("^", self._toggle_maximized),
            ("X", self.close),
        ):
            button = QPushButton(label)
            button.setObjectName("window-button")
            button.clicked.connect(handler)
            layout.addWidget(button)
        return titlebar

    def _menubar(self):
        menubar = QWidget()
        menubar.setObjectName("menubar")
        layout = QHBoxLayout(menubar)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)
        for text in ("File", "Edit", "View", "Tools", "Help"):
            button = QToolButton()
            button.setText(text)
            button.setObjectName("menu-item")
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setMenu(self._build_menu(text))
            self.menu_buttons[text] = button
            layout.addWidget(button)
        layout.addStretch(1)
        return menubar

    def _build_menu(self, title: str):
        menu = QMenu(self)
        menu.setObjectName("retro-menu")
        if title == "File":
            menu.addAction("Fetch Info", self._menu_fetch_info)
            menu.addAction("Add to Queue", self._menu_add_to_queue)
            menu.addAction("Download Now", self._menu_download_now)
            menu.addSeparator()
            menu.addAction("Browse Output Folder", self._menu_browse_output)
            menu.addSeparator()
            menu.addAction("Exit", self.close)
        elif title == "Edit":
            menu.addAction("Paste URL", self._menu_paste_url)
            menu.addAction("Clear URL", self.download_tab.url_input.clear)
            menu.addAction("Clear Log", self.download_tab.log_output.clear)
        elif title == "View":
            for index, label in enumerate(("Download", "Queue", "History", "Config")):
                menu.addAction(label, lambda _checked=False, i=index: self._activate_nav(i))
            menu.addSeparator()
            menu.addAction("Refresh History", self.history_tab.refresh)
        elif title == "Tools":
            menu.addAction("Open Output Folder", self._menu_open_output_folder)
            menu.addAction("Open Config Folder", self._menu_open_config_folder)
            menu.addSeparator()
            menu.addAction("Save Config", self.settings_tab.save)
            menu.addAction("Check yt-dlp Engine", self._menu_check_engine)
        elif title == "Help":
            menu.addAction("About YT-Studio", self._menu_about)
            menu.addAction("StreamIMDb Support Status", self._menu_check_engine)
        return menu

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

    def _toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _menu_fetch_info(self):
        self._activate_nav(0)
        self.download_tab.fetch_info()

    def _menu_add_to_queue(self):
        self._activate_nav(0)
        self.download_tab.add_to_queue()

    def _menu_download_now(self):
        self._activate_nav(0)
        self.download_tab.start_download()

    def _menu_browse_output(self):
        self._activate_nav(0)
        self.download_tab.choose_output_dir()

    def _menu_paste_url(self):
        self._activate_nav(0)
        text = QApplication.clipboard().text().strip()
        if text:
            self.download_tab.url_input.setText(text)
            self.download_tab.url_input.setFocus()

    def _menu_open_output_folder(self):
        folder = Path(self.download_tab.output_input.text().strip()).expanduser()
        self._open_folder(folder, "Output folder")

    def _menu_open_config_folder(self):
        self._open_folder(self.history_store.db_path.parent, "Config folder")

    def _open_folder(self, folder: Path, label: str):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "YT-Studio", f"{label} could not be created:\n{exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _menu_check_engine(self):
        try:
            import yt_dlp
            from yt_dlp.extractor import gen_extractors

            source = Path(yt_dlp.__file__).resolve()
            supported = [
                ie.IE_NAME
                for ie in gen_extractors()
                if ie.suitable("https://streamimdb.ru/embed/movie/tt15940132") and ie.IE_NAME != "generic"
            ]
            status = "SUPPORTED" if supported else "NOT SUPPORTED"
            detail = ", ".join(supported) if supported else "No dedicated extractor found"
            QMessageBox.information(
                self,
                "yt-dlp Engine",
                f"yt-dlp source:\n{source}\n\nStreamIMDb: {status}\n{detail}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "yt-dlp Engine", f"Could not inspect yt-dlp:\n{exc}")

    def _menu_about(self):
        QMessageBox.information(
            self,
            "About YT-Studio",
            "YT-Studio v1.0\nRetro Windows GUI for yt-dlp.\n\n"
            f"Python: {sys.version.split()[0]}",
        )
