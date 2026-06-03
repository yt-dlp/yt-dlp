from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


DONE_STATUSES = {"DONE", "FAILED", "CANCELED"}


@dataclass(slots=True)
class QueueItem:
    queue_id: int
    job: object
    title: str
    format_id: str
    progress: int = 0
    status: str = "WAIT"


class QueueTab(QWidget):
    start_requested = Signal(int, object)
    pause_requested = Signal(int)

    def __init__(self):
        super().__init__()
        self._next_id = 1
        self.items: dict[int, QueueItem] = {}
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Filename", "Format", "Progress", "Status"])
        self.start_all_button = QPushButton("START ALL")
        self.start_selected_button = QPushButton("START")
        self.pause_button = QPushButton("PAUSE")
        self.resume_button = QPushButton("RESUME")
        self.done_button = QPushButton("DONE")
        self.remove_button = QPushButton("REMOVE")
        self.clear_done_button = QPushButton("CLEAR DONE")
        self._build_layout()
        self._connect()

    def _build_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        title = QLabel("DOWNLOAD QUEUE")
        title.setStyleSheet("color:#ffb800;font-size:16px;font-weight:700")
        header.addWidget(title)
        header.addStretch(1)
        for button in (
            self.start_all_button,
            self.start_selected_button,
            self.pause_button,
            self.resume_button,
            self.done_button,
            self.remove_button,
            self.clear_done_button,
        ):
            header.addWidget(button)
        root.addLayout(header)
        root.addWidget(self.table, 1)

    def _connect(self):
        self.start_all_button.clicked.connect(self.start_next_waiting)
        self.start_selected_button.clicked.connect(self.start_selected)
        self.pause_button.clicked.connect(self.pause_selected)
        self.resume_button.clicked.connect(self.resume_selected)
        self.done_button.clicked.connect(self.mark_selected_done)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_done_button.clicked.connect(self.clear_done)

    def add_job(self, job) -> int:
        queue_id = self._next_id
        self._next_id += 1
        title = getattr(job, "title", "") or getattr(job, "url", "")
        format_id = getattr(job, "format_id", "")
        self.items[queue_id] = QueueItem(queue_id, job, title, format_id)
        self._append_row(self.items[queue_id])
        return queue_id

    def _append_row(self, item: QueueItem):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate(self._row_values(item)):
            self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def update_job(self, queue_id: int, status: str | None = None, progress: int | None = None):
        item = self.items.get(queue_id)
        if not item:
            return
        if status:
            item.status = status
        if progress is not None:
            item.progress = max(0, min(100, int(progress)))
        row = self._row_for_id(queue_id)
        if row is not None:
            for column, value in enumerate(self._row_values(item)):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def start_next_waiting(self):
        for item in self.items.values():
            if item.status in {"WAIT", "PAUSED"}:
                self.start_requested.emit(item.queue_id, item.job)
                return

    def start_selected(self):
        item = self._selected_item()
        if item and item.status in {"WAIT", "PAUSED"}:
            self.start_requested.emit(item.queue_id, item.job)

    def pause_selected(self):
        item = self._selected_item()
        if item and item.status == "RUN":
            self.pause_requested.emit(item.queue_id)

    def resume_selected(self):
        item = self._selected_item()
        if item and item.status == "PAUSED":
            self.start_requested.emit(item.queue_id, item.job)

    def mark_selected_done(self):
        item = self._selected_item()
        if item and item.status != "RUN":
            self.update_job(item.queue_id, "DONE", 100)

    def remove_selected(self):
        item = self._selected_item()
        if not item or item.status == "RUN":
            return
        row = self._row_for_id(item.queue_id)
        if row is not None:
            self.table.removeRow(row)
        self.items.pop(item.queue_id, None)

    def clear_done(self):
        for queue_id, item in list(self.items.items()):
            if item.status in DONE_STATUSES:
                row = self._row_for_id(queue_id)
                if row is not None:
                    self.table.removeRow(row)
                self.items.pop(queue_id, None)

    def _selected_item(self) -> QueueItem | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        id_item = self.table.item(row, 0)
        if not id_item:
            return None
        return self.items.get(int(id_item.text()))

    def _row_for_id(self, queue_id: int) -> int | None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and int(item.text()) == queue_id:
                return row
        return None

    @staticmethod
    def _row_values(item: QueueItem) -> list[str]:
        return [
            str(item.queue_id),
            item.title,
            item.format_id,
            f"{item.progress}%",
            item.status,
        ]
