from PySide6.QtWidgets import QMainWindow, QTabWidget

from core.history import HistoryStore
from gui.download_tab import DownloadTab
from gui.history_tab import HistoryTab
from gui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YT-Studio")
        self.resize(980, 680)

        self.history_store = HistoryStore()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.settings_tab = SettingsTab(self.history_store)
        self.history_tab = HistoryTab(self.history_store)
        self.download_tab = DownloadTab(self.history_store, self.history_tab.refresh)

        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.history_tab, "History")
        self.tabs.addTab(self.settings_tab, "Settings")
