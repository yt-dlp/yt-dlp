from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.downloader import DownloadWorker
from core.info_fetcher import InfoWorker
from core.models import DownloadJob


FORMAT_PRESETS = {
    "Best video + audio": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "Audio MP3": "bestaudio/best",
    "Audio M4A": "bestaudio/best",
}


class DownloadTab(QWidget):
    def __init__(self, history_store, on_history_changed):
        super().__init__()
        self.history_store = history_store
        self.on_history_changed = on_history_changed
        self.info_worker = None
        self.download_worker = None
        self.current_info = {}
        self.current_download_id = None

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a video, playlist, or channel URL")
        self.fetch_button = QPushButton("Fetch info")
        self.download_button = QPushButton("Download")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        self.output_input = QLineEdit(self.history_store.get_setting("output_dir", str(Path.home() / "Downloads")))
        self.browse_button = QPushButton("Browse")
        self.format_combo = QComboBox()
        self.format_combo.addItems(FORMAT_PRESETS.keys())
        self.subtitle_input = QLineEdit("en")
        self.write_subs = QCheckBox("Download subtitles")
        self.embed_subs = QCheckBox("Embed subtitles")
        self.embed_metadata = QCheckBox("Embed metadata")
        self.embed_thumbnail = QCheckBox("Embed thumbnail")

        self.title_label = QLabel("No media loaded")
        self.title_label.setWordWrap(True)
        self.duration_label = QLabel("")
        self.status_label = QLabel("Ready")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.speed_label = QLabel("Speed: -")
        self.eta_label = QLabel("ETA: -")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)

        self._build_layout()
        self._connect()

    def _build_layout(self):
        root = QVBoxLayout(self)

        input_group = QGroupBox("Source")
        input_layout = QGridLayout(input_group)
        input_layout.addWidget(QLabel("URL"), 0, 0)
        input_layout.addWidget(self.url_input, 0, 1, 1, 3)
        input_layout.addWidget(self.fetch_button, 0, 4)
        input_layout.addWidget(QLabel("Output"), 1, 0)
        input_layout.addWidget(self.output_input, 1, 1, 1, 3)
        input_layout.addWidget(self.browse_button, 1, 4)
        root.addWidget(input_group)

        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        options_layout.addRow("Format", self.format_combo)
        options_layout.addRow("Subtitle languages", self.subtitle_input)
        options_layout.addRow(self.write_subs)
        options_layout.addRow(self.embed_subs)
        options_layout.addRow(self.embed_metadata)
        options_layout.addRow(self.embed_thumbnail)
        root.addWidget(options_group)

        info_group = QGroupBox("Media")
        info_layout = QVBoxLayout(info_group)
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.duration_label)
        root.addWidget(info_group)

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress)
        progress_row.addWidget(self.speed_label)
        progress_row.addWidget(self.eta_label)
        root.addLayout(progress_row)
        root.addWidget(self.status_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.download_button)
        root.addLayout(actions)
        root.addWidget(self.log_output)

    def _connect(self):
        self.fetch_button.clicked.connect(self.fetch_info)
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.browse_button.clicked.connect(self.choose_output_dir)

    def choose_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_input.text())
        if folder:
            self.output_input.setText(folder)
            self.history_store.set_setting("output_dir", folder)

    def fetch_info(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Paste a URL first.")
            return
        self.fetch_button.setEnabled(False)
        self.status_label.setText("Fetching media info...")
        self.info_worker = InfoWorker(url, self.history_store.get_settings())
        self.info_worker.fetched.connect(self._info_fetched)
        self.info_worker.error.connect(self._worker_error)
        self.info_worker.finished.connect(lambda: self.fetch_button.setEnabled(True))
        self.info_worker.start()

    def _info_fetched(self, info):
        self.current_info = info or {}
        title = self.current_info.get("title") or self.url_input.text().strip()
        duration = self.current_info.get("duration")
        self.title_label.setText(title)
        self.duration_label.setText(f"Duration: {self._format_duration(duration)}" if duration else "")
        self.status_label.setText("Media info loaded")

    def start_download(self):
        url = self.url_input.text().strip()
        output_dir = Path(self.output_input.text().strip())
        if not url:
            QMessageBox.warning(self, "Missing URL", "Paste a URL first.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Missing folder", "Choose an output folder first.")
            return

        preset = self.format_combo.currentText()
        job = DownloadJob(
            url=url,
            output_dir=output_dir,
            format_id=FORMAT_PRESETS[preset],
            title=self.current_info.get("title", ""),
            audio_only=preset.startswith("Audio"),
            audio_format="m4a" if preset.endswith("M4A") else "mp3",
            write_subs=self.write_subs.isChecked(),
            embed_subs=self.embed_subs.isChecked(),
            subtitle_language=self.subtitle_input.text(),
            embed_metadata=self.embed_metadata.isChecked(),
            embed_thumbnail=self.embed_thumbnail.isChecked(),
        )

        self.current_download_id = self.history_store.add_download(
            title=job.title or job.url,
            url=job.url,
            output_path=str(job.output_dir),
            format_id=job.format_id,
            status="running",
        )
        self.history_store.set_setting("output_dir", str(output_dir))
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setValue(0)
        self.status_label.setText("Starting download...")

        self.download_worker = DownloadWorker(job, self.history_store.get_settings())
        self.download_worker.progress.connect(self._download_progress)
        self.download_worker.status.connect(self.status_label.setText)
        self.download_worker.error.connect(self._download_error)
        self.download_worker.finished.connect(self._download_finished)
        self.download_worker.canceled.connect(self._download_canceled)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker:
            self.download_worker.cancel()
            self.status_label.setText("Cancel requested...")

    def _download_progress(self, event):
        self.progress.setValue(int(event["percent"]))
        self.speed_label.setText(f"Speed: {self._format_speed(event.get('speed'))}")
        self.eta_label.setText(f"ETA: {self._format_duration(event.get('eta'))}")
        if event.get("filename"):
            self.log_output.append(event["filename"])

    def _download_finished(self, _event):
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "completed")
        self.status_label.setText("Download complete")
        self.progress.setValue(100)
        self._reset_download_buttons()
        self.on_history_changed()

    def _download_canceled(self):
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "canceled")
        self.status_label.setText("Download canceled")
        self._reset_download_buttons()
        self.on_history_changed()

    def _download_error(self, message):
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "failed", message)
        self._worker_error(message)
        self._reset_download_buttons()
        self.on_history_changed()

    def _worker_error(self, message):
        self.status_label.setText("Error")
        self.log_output.append(message)
        QMessageBox.warning(self, "YT-Studio", message)

    def _reset_download_buttons(self):
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    @staticmethod
    def _format_speed(speed):
        if not speed:
            return "-"
        return f"{speed / 1024 / 1024:.2f} MB/s"

    @staticmethod
    def _format_duration(seconds):
        if seconds is None:
            return "-"
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{sec:02d}"
        return f"{minutes}:{sec:02d}"
