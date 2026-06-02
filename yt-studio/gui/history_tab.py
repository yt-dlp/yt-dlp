from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class HistoryTab(QWidget):
    def __init__(self, history_store):
        super().__init__()
        self.history_store = history_store
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history")
        self.refresh_button = QPushButton("Refresh")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Title", "URL", "Output", "Format", "Status", "Completed"])

        root = QVBoxLayout(self)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search"))
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.refresh_button)
        root.addLayout(search_row)
        root.addWidget(self.table)

        self.search_input.textChanged.connect(self.refresh)
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh()

    def refresh(self):
        rows = self.history_store.search_downloads(self.search_input.text().strip())
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row["title"],
                row["url"],
                row["output_path"],
                row["format"],
                row["status"],
                row["completed_at"] or "",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
