from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class QueueTab(QWidget):
    def __init__(self):
        super().__init__()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Filename", "Format", "Progress", "Status"])
        self.start_all_button = QPushButton("START ALL")
        self.clear_done_button = QPushButton("CLEAR DONE")
        self.clear_done_button.clicked.connect(self.clear_done)
        self._build_layout()

    def _build_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        title = QLabel("DOWNLOAD QUEUE")
        title.setStyleSheet("color:#ffb800;font-size:16px;font-weight:700")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.start_all_button)
        header.addWidget(self.clear_done_button)
        root.addLayout(header)
        root.addWidget(self.table, 1)

    def add_job(self, title: str, format_id: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [f"{row + 1:02d}", title, format_id, "0%", "WAIT"]
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()

    def mark_latest_running(self):
        if self.table.rowCount():
            self.table.setItem(self.table.rowCount() - 1, 4, QTableWidgetItem("RUN"))

    def clear_done(self):
        for row in reversed(range(self.table.rowCount())):
            item = self.table.item(row, 4)
            if item and item.text() in {"DONE", "FAILED", "CANCELED"}:
                self.table.removeRow(row)
