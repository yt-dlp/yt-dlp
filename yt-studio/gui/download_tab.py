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
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.downloader import DownloadWorker
from core.info_fetcher import InfoWorker
from core.models import DownloadJob
from core.ui_state import context_from_info, visible_sections


QUALITY_PRESETS = {
    "Best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "Audio MP3": "bestaudio/best",
    "Audio M4A": "bestaudio/best",
}
SUBTITLE_LANGS = {"Off": "", "English": "en", "Arabic": "ar", "All": "all"}
SPONSORBLOCK = {"Off": "off", "Mark only": "mark", "Skip sponsors": "skip"}
FILENAME_PRESETS = {
    "%(title)s": "title",
    "%(uploader)s-%(title)s": "uploader-title",
    "%(date)s-%(title)s": "date-title",
}
AUDIO_QUALITY = {"Best": "0", "Normal": "5", "192K": "192K", "128K": "128K"}


class DownloadTab(QWidget):
    def __init__(self, history_store, on_history_changed, on_queue_added):
        super().__init__()
        self.history_store = history_store
        self.on_history_changed = on_history_changed
        self.on_queue_added = on_queue_added
        self.info_worker = None
        self.download_worker = None
        self.current_info = {}
        self.current_download_id = None

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self.fetch_button = QPushButton("[ FETCH ]")
        self.download_button = QPushButton("DOWNLOAD NOW")
        self.download_button.setObjectName("primary-button")
        self.add_queue_button = QPushButton("ADD TO QUEUE")
        self.cancel_button = QPushButton("CANCEL")
        self.cancel_button.setEnabled(False)

        self.title_label = QLabel("No media loaded")
        self.title_label.setWordWrap(True)
        self.meta_label = QLabel("DUR: --   VIEWS: --   SRC: --")

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_PRESETS.keys())
        self.quality_combo.setCurrentText("1080p")
        self.container_combo = QComboBox()
        self.container_combo.addItems(["MP4", "MKV", "WEBM"])
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems(AUDIO_QUALITY.keys())
        self.audio_quality_combo.setCurrentText("Normal")

        self.embed_metadata = QCheckBox("EMBED METADATA")
        self.embed_metadata.setChecked(True)
        self.embed_thumbnail = QCheckBox("EMBED THUMBNAIL")
        self.embed_thumbnail.setChecked(True)
        self.subtitles_combo = QComboBox()
        self.subtitles_combo.addItems(SUBTITLE_LANGS.keys())
        self.embed_subs = QCheckBox("EMBED SUBS")
        self.auto_subs = QCheckBox("AUTO SUBS")
        self.auto_subs.setChecked(True)

        self.output_input = QLineEdit(self.history_store.get_setting("output_dir", str(Path.home() / "Downloads")))
        self.browse_button = QPushButton("BROWSE")
        self.filename_combo = QComboBox()
        self.filename_combo.addItems(FILENAME_PRESETS.keys())
        self.skip_existing = QCheckBox("SKIP EXISTING")
        self.skip_existing.setChecked(True)

        self.sponsorblock_combo = QComboBox()
        self.sponsorblock_combo.addItems(SPONSORBLOCK.keys())
        self.sponsorblock_combo.setCurrentText("Skip sponsors")
        self.split_chapters = QCheckBox("SPLIT CHAPTERS")
        self.playlist_mode = QCheckBox("PLAYLIST MODE")
        self.playlist_items_label = QLabel("ITEMS")
        self.playlist_items = QLineEdit()
        self.playlist_items.setPlaceholderText("1:5")
        self.max_downloads_label = QLabel("MAX")
        self.max_downloads = QSpinBox()
        self.max_downloads.setRange(0, 9999)
        self.max_downloads.setSpecialValueText("ALL")
        self.live_from_start = QCheckBox("LIVE FROM START")
        self.wait_for_video_label = QLabel("WAIT")
        self.wait_for_video = QLineEdit()
        self.wait_for_video.setPlaceholderText("30-120")

        self.status_label = QLabel("STATUS: READY")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.speed_label = QLabel("SPEED: -")
        self.eta_label = QLabel("ETA: -")
        self.size_label = QLabel("SIZE: -")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(82)

        self._build_layout()
        self._connect()
        self._apply_contextual_visibility()

    def _build_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addLayout(self._url_row())
        root.addLayout(self._info_row())

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(self._format_group(), 0, 0)
        grid.addWidget(self._enrich_group(), 0, 1)
        grid.addWidget(self._output_group(), 1, 0)
        grid.addWidget(self._content_group(), 1, 1)
        root.addLayout(grid)

        root.addWidget(self._progress_group())
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.add_queue_button)
        actions.addWidget(self.download_button)
        root.addLayout(actions)
        root.addWidget(self.log_output)

    def _url_row(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("C:\\> ENTER URL:"))
        row = QHBoxLayout()
        row.addWidget(QLabel("URL>"))
        row.addWidget(self.url_input, 1)
        row.addWidget(self.fetch_button)
        layout.addLayout(row)
        return layout

    def _info_row(self):
        layout = QHBoxLayout()
        thumb = QLabel("VIDEO")
        thumb.setFixedSize(72, 48)
        thumb.setStyleSheet("border:1px solid #0d4d00;color:#0d4d00")
        layout.addWidget(thumb)
        info = QVBoxLayout()
        info.addWidget(self.title_label)
        info.addWidget(self.meta_label)
        layout.addLayout(info, 1)
        return layout

    def _format_group(self):
        group = QGroupBox("[ FORMAT ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("QUALITY"), 0, 0)
        layout.addWidget(self.quality_combo, 0, 1)
        layout.addWidget(QLabel("CONTAINER"), 1, 0)
        layout.addWidget(self.container_combo, 1, 1)
        layout.addWidget(QLabel("AUDIO Q."), 2, 0)
        layout.addWidget(self.audio_quality_combo, 2, 1)
        return group

    def _enrich_group(self):
        group = QGroupBox("[ ENRICH ]")
        layout = QGridLayout(group)
        layout.addWidget(self.embed_metadata, 0, 0)
        layout.addWidget(self.embed_thumbnail, 1, 0)
        layout.addWidget(QLabel("SUBTITLES"), 2, 0)
        layout.addWidget(self.subtitles_combo, 2, 1)
        layout.addWidget(self.embed_subs, 3, 0)
        layout.addWidget(self.auto_subs, 3, 1)
        return group

    def _output_group(self):
        group = QGroupBox("[ OUTPUT ]")
        layout = QGridLayout(group)
        layout.addWidget(self.output_input, 0, 0)
        layout.addWidget(self.browse_button, 0, 1)
        layout.addWidget(QLabel("FILENAME"), 1, 0)
        layout.addWidget(self.filename_combo, 1, 1)
        layout.addWidget(self.skip_existing, 2, 0, 1, 2)
        return group

    def _content_group(self):
        group = QGroupBox("[ CONTENT ]")
        layout = QGridLayout(group)
        layout.addWidget(QLabel("SPONSORBLOCK"), 0, 0)
        layout.addWidget(self.sponsorblock_combo, 0, 1)
        layout.addWidget(self.split_chapters, 1, 0, 1, 2)
        layout.addWidget(self.playlist_mode, 2, 0, 1, 2)
        layout.addWidget(self.playlist_items_label, 3, 0)
        layout.addWidget(self.playlist_items, 3, 1)
        layout.addWidget(self.max_downloads_label, 4, 0)
        layout.addWidget(self.max_downloads, 4, 1)
        layout.addWidget(self.live_from_start, 5, 0, 1, 2)
        layout.addWidget(self.wait_for_video_label, 6, 0)
        layout.addWidget(self.wait_for_video, 6, 1)
        return group

    def _progress_group(self):
        group = QGroupBox("STATUS: READY")
        layout = QVBoxLayout(group)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        row.addWidget(QLabel("0%"))
        row.addWidget(self.speed_label)
        row.addWidget(self.eta_label)
        row.addWidget(self.size_label)
        layout.addLayout(row)
        return group

    def _connect(self):
        self.fetch_button.clicked.connect(self.fetch_info)
        self.download_button.clicked.connect(self.start_download)
        self.add_queue_button.clicked.connect(self.add_to_queue)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.browse_button.clicked.connect(self.choose_output_dir)
        self.quality_combo.currentTextChanged.connect(self._apply_contextual_visibility)
        self.subtitles_combo.currentTextChanged.connect(self._apply_contextual_visibility)
        self.sponsorblock_combo.currentTextChanged.connect(self._apply_contextual_visibility)

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
        self.status_label.setText("STATUS: FETCHING MEDIA INFO...")
        self.info_worker = InfoWorker(url, self.history_store.get_settings())
        self.info_worker.fetched.connect(self._info_fetched)
        self.info_worker.error.connect(self._worker_error)
        self.info_worker.finished.connect(lambda: self.fetch_button.setEnabled(True))
        self.info_worker.start()

    def _info_fetched(self, info):
        self.current_info = info or {}
        title = self.current_info.get("title") or self.url_input.text().strip()
        duration = self.current_info.get("duration")
        view_count = self.current_info.get("view_count")
        extractor = self.current_info.get("extractor_key") or self.current_info.get("extractor", "--")
        self.title_label.setText(title)
        self.meta_label.setText(
            f"DUR: {self._format_duration(duration)}   VIEWS: {self._format_count(view_count)}   SRC: {extractor.upper()}"
        )
        self.status_label.setText("STATUS: MEDIA INFO LOADED")
        self._apply_contextual_visibility()

    def _selected_job(self) -> DownloadJob:
        preset = self.quality_combo.currentText()
        subtitles = self.subtitles_combo.currentText()
        max_downloads = self.max_downloads.value() or None
        return DownloadJob(
            url=self.url_input.text().strip(),
            output_dir=Path(self.output_input.text().strip()),
            format_id=QUALITY_PRESETS[preset],
            title=self.current_info.get("title", ""),
            container=self.container_combo.currentText().lower(),
            filename_preset=FILENAME_PRESETS[self.filename_combo.currentText()],
            skip_existing=self.skip_existing.isChecked(),
            audio_only=preset.startswith("Audio"),
            audio_format="m4a" if preset.endswith("M4A") else "mp3",
            audio_quality=AUDIO_QUALITY[self.audio_quality_combo.currentText()],
            write_subs=subtitles != "Off",
            write_auto_subs=self.auto_subs.isChecked(),
            embed_subs=self.embed_subs.isChecked(),
            subtitle_language=SUBTITLE_LANGS[subtitles],
            embed_metadata=self.embed_metadata.isChecked(),
            embed_thumbnail=self.embed_thumbnail.isChecked(),
            sponsorblock_mode=SPONSORBLOCK[self.sponsorblock_combo.currentText()],
            split_chapters=self.split_chapters.isChecked(),
            playlist_mode=self.playlist_mode.isChecked(),
            playlist_items=self.playlist_items.text().strip(),
            max_downloads=max_downloads,
            live_from_start=self.live_from_start.isChecked(),
            wait_for_video=self.wait_for_video.text().strip(),
        )

    def add_to_queue(self):
        if not self.url_input.text().strip():
            QMessageBox.warning(self, "Missing URL", "Paste a URL first.")
            return
        job = self._selected_job()
        self.on_queue_added(job.title or job.url, job.format_id)
        self.status_label.setText("STATUS: ADDED TO QUEUE")

    def start_download(self):
        url = self.url_input.text().strip()
        output_dir = Path(self.output_input.text().strip())
        if not url:
            QMessageBox.warning(self, "Missing URL", "Paste a URL first.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Missing folder", "Choose an output folder first.")
            return

        job = self._selected_job()
        self.on_queue_added(job.title or job.url, job.format_id)

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
        self.status_label.setText("STATUS: STARTING DOWNLOAD...")

        self.download_worker = DownloadWorker(job, self.history_store.get_settings())
        self.download_worker.progress.connect(self._download_progress)
        self.download_worker.status.connect(lambda text: self.status_label.setText(f"STATUS: {text.upper()}"))
        self.download_worker.error.connect(self._download_error)
        self.download_worker.finished.connect(self._download_finished)
        self.download_worker.canceled.connect(self._download_canceled)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker:
            self.download_worker.cancel()
            self.status_label.setText("STATUS: CANCEL REQUESTED...")

    def _download_progress(self, event):
        self.progress.setValue(int(event["percent"]))
        self.speed_label.setText(f"SPEED: {self._format_speed(event.get('speed'))}")
        self.eta_label.setText(f"ETA: {self._format_duration(event.get('eta'))}")
        if event.get("filename"):
            self.log_output.append(event["filename"])

    def _download_finished(self, event):
        warning = (event or {}).get("warning")
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "completed", warning)
        if warning:
            self.status_label.setText("STATUS: DOWNLOAD COMPLETE - POST-PROCESS WARNING")
            self.log_output.append(warning)
        else:
            self.status_label.setText("STATUS: DOWNLOAD COMPLETE")
        self.progress.setValue(100)
        self._reset_download_buttons()
        self.on_history_changed()

    def _download_canceled(self):
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "canceled")
        self.status_label.setText("STATUS: DOWNLOAD CANCELED")
        self._reset_download_buttons()
        self.on_history_changed()

    def _download_error(self, message):
        if self.current_download_id:
            self.history_store.finish_download(self.current_download_id, "failed", message)
        self._worker_error(message)
        self._reset_download_buttons()
        self.on_history_changed()

    def _worker_error(self, message):
        self.status_label.setText("STATUS: ERROR")
        self.log_output.append(message)
        QMessageBox.warning(self, "YT-Studio", message)

    def _reset_download_buttons(self):
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def _apply_contextual_visibility(self):
        context = context_from_info(
            self.current_info,
            quality=self.quality_combo.currentText(),
            subtitles=self.subtitles_combo.currentText(),
            sponsorblock_mode=self.sponsorblock_combo.currentText(),
        )
        sections = visible_sections(context)
        self.container_combo.setEnabled(sections["video_container"])
        self.playlist_mode.setVisible(sections["playlist"])
        self.playlist_items_label.setVisible(sections["playlist"])
        self.playlist_items.setVisible(sections["playlist"])
        self.max_downloads_label.setVisible(sections["playlist"])
        self.max_downloads.setVisible(sections["playlist"])
        self.live_from_start.setVisible(sections["live"])
        self.wait_for_video_label.setVisible(sections["live"])
        self.wait_for_video.setVisible(sections["live"])
        self.embed_subs.setVisible(sections["subtitle_details"])
        self.auto_subs.setVisible(sections["subtitle_details"])
        if sections["playlist"]:
            self.playlist_mode.setChecked(True)

    @staticmethod
    def _format_speed(speed):
        if not speed:
            return "-"
        return f"{speed / 1024 / 1024:.2f} MB/S"

    @staticmethod
    def _format_duration(seconds):
        if seconds is None:
            return "--"
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{sec:02d}"
        return f"{minutes}:{sec:02d}"

    @staticmethod
    def _format_count(value):
        if value is None:
            return "--"
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"{value / 1_000:.1f}K"
        return str(value)
