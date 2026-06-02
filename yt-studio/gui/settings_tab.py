from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget


class SettingsTab(QWidget):
    def __init__(self, history_store):
        super().__init__()
        self.history_store = history_store
        settings = self.history_store.get_settings()

        self.output_dir = QLineEdit(settings.get("output_dir", str(Path.home() / "Downloads")))
        self.cookies_file = QLineEdit(settings.get("cookies_file", ""))
        self.proxy = QLineEdit(settings.get("proxy", ""))
        self.rate_limit = QLineEdit(settings.get("rate_limit", ""))
        self.user_agent = QLineEdit(settings.get("user_agent", ""))
        self.ffmpeg_location = QLineEdit(settings.get("ffmpeg_location", ""))

        self.save_button = QPushButton("Save settings")
        self.output_browse = QPushButton("Browse")
        self.cookies_browse = QPushButton("Browse")

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Default output folder", self._with_button(self.output_dir, self.output_browse))
        form.addRow("Cookies file", self._with_button(self.cookies_file, self.cookies_browse))
        form.addRow("Proxy", self.proxy)
        form.addRow("Rate limit", self.rate_limit)
        form.addRow("User agent", self.user_agent)
        form.addRow("FFmpeg location", self.ffmpeg_location)
        root.addLayout(form)
        root.addWidget(self.save_button)
        root.addStretch(1)

        self.save_button.clicked.connect(self.save)
        self.output_browse.clicked.connect(self.choose_output_dir)
        self.cookies_browse.clicked.connect(self.choose_cookies_file)

    def _with_button(self, field, button):
        row = QHBoxLayout()
        row.addWidget(field)
        row.addWidget(button)
        container = QWidget()
        container.setLayout(row)
        return container

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose default output folder", self.output_dir.text())
        if folder:
            self.output_dir.setText(folder)

    def choose_cookies_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Choose cookies file", "", "Text files (*.txt);;All files (*)")
        if filename:
            self.cookies_file.setText(filename)

    def save(self):
        values = {
            "output_dir": self.output_dir.text().strip(),
            "cookies_file": self.cookies_file.text().strip(),
            "proxy": self.proxy.text().strip(),
            "rate_limit": self.rate_limit.text().strip(),
            "user_agent": self.user_agent.text().strip(),
            "ffmpeg_location": self.ffmpeg_location.text().strip(),
        }
        for key, value in values.items():
            self.history_store.set_setting(key, value)
