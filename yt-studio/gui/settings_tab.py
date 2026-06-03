from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsTab(QWidget):
    def __init__(self, history_store):
        super().__init__()
        self.history_store = history_store
        settings = self.history_store.get_settings()

        self.output_dir = QLineEdit(settings.get("output_dir", str(Path.home() / "Downloads")))
        self.concurrent_downloads = self._spin(1, 4, int(settings.get("concurrent_downloads", "2") or 2))
        self.concurrent_fragments = self._spin(1, 16, int(settings.get("concurrent_fragments", "4") or 4))
        self.rate_limit = QLineEdit(settings.get("rate_limit", ""))
        self.retries = self._spin(0, 999, int(settings.get("retries", "10") or 10))
        self.download_archive_enabled = QCheckBox("DOWNLOAD ARCHIVE (NO REDOWNLOAD)")
        self.download_archive_enabled.setChecked(settings.get("download_archive_enabled", "true") != "false")
        self.download_archive = QLineEdit(settings.get("download_archive", ""))

        self.proxy = QLineEdit(settings.get("proxy", ""))
        self.impersonate = QComboBox()
        self.impersonate.addItems(["", "chrome", "chrome:windows-10", "firefox", "safari"])
        self.impersonate.setCurrentText(settings.get("impersonate", ""))
        self.force_ip = QComboBox()
        self.force_ip.addItems(["auto", "ipv4", "ipv6"])
        self.force_ip.setCurrentText(settings.get("force_ip", "auto"))
        self.socket_timeout = self._spin(0, 300, int(settings.get("socket_timeout", "0") or 0))

        self.cookies_from_browser = QComboBox()
        self.cookies_from_browser.addItems(["", "chrome", "firefox", "edge", "brave", "vivaldi"])
        self.cookies_from_browser.setCurrentText(settings.get("cookies_from_browser", ""))
        self.cookies_file = QLineEdit(settings.get("cookies_file", ""))
        self.wyzie_api_key = QLineEdit(settings.get("wyzie_api_key", ""))
        self.subdl_api_key = QLineEdit(settings.get("subdl_api_key", ""))

        self.ffmpeg_location = QLineEdit(settings.get("ffmpeg_location", ""))
        self.temp_path = QLineEdit(settings.get("paths_temp", ""))
        self.keep_part = QCheckBox("KEEP PARTIAL FILES")
        self.keep_part.setChecked(settings.get("keep_part", "true") != "false")

        self.save_button = QPushButton("SAVE CONFIG")
        self.save_button.setObjectName("primary-button")
        self.reset_button = QPushButton("RESET DEFAULTS")
        self.output_browse = QPushButton("BROWSE")
        self.cookies_browse = QPushButton("BROWSE")
        self.ffmpeg_browse = QPushButton("BROWSE")
        self.temp_browse = QPushButton("BROWSE")

        self._build_layout()
        self._connect()

    def _build_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        title = QLabel("SYSTEM CONFIGURATION")
        title.setStyleSheet("color:#ffb800;font-size:16px;font-weight:700")
        root.addWidget(title)

        grid = QGridLayout()
        grid.addWidget(self._general_group(), 0, 0)
        grid.addWidget(self._network_group(), 0, 1)
        grid.addWidget(self._auth_group(), 1, 0)
        grid.addWidget(self._files_group(), 1, 1)
        root.addLayout(grid)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.reset_button)
        actions.addWidget(self.save_button)
        root.addLayout(actions)
        root.addStretch(1)

    def _general_group(self):
        group = QGroupBox("[ GENERAL ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("DEFAULT OUTPUT PATH"), 0, 0)
        layout.addWidget(self.output_dir, 0, 1)
        layout.addWidget(self.output_browse, 0, 2)
        layout.addWidget(QLabel("CONCURRENT DOWNLOADS"), 1, 0)
        layout.addWidget(self.concurrent_downloads, 1, 1)
        layout.addWidget(QLabel("FRAGMENT THREADS"), 2, 0)
        layout.addWidget(self.concurrent_fragments, 2, 1)
        layout.addWidget(QLabel("RATE LIMIT"), 3, 0)
        layout.addWidget(self.rate_limit, 3, 1)
        layout.addWidget(QLabel("RETRY COUNT"), 4, 0)
        layout.addWidget(self.retries, 4, 1)
        layout.addWidget(self.download_archive_enabled, 5, 0, 1, 3)
        layout.addWidget(QLabel("ARCHIVE FILE"), 6, 0)
        layout.addWidget(self.download_archive, 6, 1, 1, 2)
        return group

    def _network_group(self):
        group = QGroupBox("[ NETWORK ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("PROXY SERVER"), 0, 0)
        layout.addWidget(self.proxy, 0, 1)
        layout.addWidget(QLabel("IMPERSONATE"), 1, 0)
        layout.addWidget(self.impersonate, 1, 1)
        layout.addWidget(QLabel("FORCE IP"), 2, 0)
        layout.addWidget(self.force_ip, 2, 1)
        layout.addWidget(QLabel("SOCKET TIMEOUT"), 3, 0)
        layout.addWidget(self.socket_timeout, 3, 1)
        return group

    def _auth_group(self):
        group = QGroupBox("[ AUTHENTICATION ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("COOKIES FROM BROWSER"), 0, 0)
        layout.addWidget(self.cookies_from_browser, 0, 1)
        layout.addWidget(QLabel("COOKIES FILE"), 1, 0)
        layout.addWidget(self.cookies_file, 1, 1)
        layout.addWidget(self.cookies_browse, 1, 2)
        layout.addWidget(QLabel("WYZE/WYZIE SUBS API KEY"), 2, 0)
        layout.addWidget(self.wyzie_api_key, 2, 1, 1, 2)
        layout.addWidget(QLabel("SUBDL SUBS API KEY"), 3, 0)
        layout.addWidget(self.subdl_api_key, 3, 1, 1, 2)
        return group

    def _files_group(self):
        group = QGroupBox("[ FILES / UPDATES ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("FFMPEG LOCATION"), 0, 0)
        layout.addWidget(self.ffmpeg_location, 0, 1)
        layout.addWidget(self.ffmpeg_browse, 0, 2)
        layout.addWidget(QLabel("TEMP FOLDER"), 1, 0)
        layout.addWidget(self.temp_path, 1, 1)
        layout.addWidget(self.temp_browse, 1, 2)
        layout.addWidget(self.keep_part, 2, 0, 1, 3)
        layout.addWidget(QLabel("YT-DLP VERSION: 2026.03.17"), 3, 0, 1, 3)
        layout.addWidget(QLabel("FFMPEG STATUS: CHECKED AT BUILD/RUNTIME"), 4, 0, 1, 3)
        return group

    def _connect(self):
        self.save_button.clicked.connect(self.save)
        self.reset_button.clicked.connect(self.reset_defaults)
        self.output_browse.clicked.connect(self.choose_output_dir)
        self.cookies_browse.clicked.connect(self.choose_cookies_file)
        self.ffmpeg_browse.clicked.connect(self.choose_ffmpeg_location)
        self.temp_browse.clicked.connect(self.choose_temp_dir)

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose default output folder", self.output_dir.text())
        if folder:
            self.output_dir.setText(folder)

    def choose_cookies_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Choose cookies file", "", "Text files (*.txt);;All files (*)")
        if filename:
            self.cookies_file.setText(filename)

    def choose_ffmpeg_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose FFmpeg folder", self.ffmpeg_location.text())
        if folder:
            self.ffmpeg_location.setText(folder)

    def choose_temp_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose temp folder", self.temp_path.text())
        if folder:
            self.temp_path.setText(folder)

    def reset_defaults(self):
        self.output_dir.setText(str(Path.home() / "Downloads"))
        self.concurrent_downloads.setValue(2)
        self.concurrent_fragments.setValue(4)
        self.rate_limit.clear()
        self.retries.setValue(10)
        self.download_archive_enabled.setChecked(True)
        self.download_archive.clear()
        self.proxy.clear()
        self.impersonate.setCurrentText("")
        self.force_ip.setCurrentText("auto")
        self.socket_timeout.setValue(0)
        self.cookies_from_browser.setCurrentText("")
        self.cookies_file.clear()
        self.wyzie_api_key.clear()
        self.subdl_api_key.clear()
        self.ffmpeg_location.clear()
        self.temp_path.clear()
        self.keep_part.setChecked(True)

    def save(self):
        values = {
            "output_dir": self.output_dir.text().strip(),
            "concurrent_downloads": str(self.concurrent_downloads.value()),
            "concurrent_fragments": str(self.concurrent_fragments.value()),
            "rate_limit": self.rate_limit.text().strip(),
            "retries": str(self.retries.value()),
            "download_archive_enabled": str(self.download_archive_enabled.isChecked()).lower(),
            "download_archive": self.download_archive.text().strip() if self.download_archive_enabled.isChecked() else "",
            "proxy": self.proxy.text().strip(),
            "impersonate": self.impersonate.currentText(),
            "force_ip": self.force_ip.currentText(),
            "socket_timeout": str(self.socket_timeout.value()) if self.socket_timeout.value() else "",
            "cookies_from_browser": self.cookies_from_browser.currentText(),
            "cookies_file": self.cookies_file.text().strip(),
            "wyzie_api_key": self.wyzie_api_key.text().strip(),
            "subdl_api_key": self.subdl_api_key.text().strip(),
            "ffmpeg_location": self.ffmpeg_location.text().strip(),
            "paths_temp": self.temp_path.text().strip(),
            "keep_part": str(self.keep_part.isChecked()).lower(),
        }
        for key, value in values.items():
            self.history_store.set_setting(key, value)

    @staticmethod
    def _spin(minimum: int, maximum: int, value: int):
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin
