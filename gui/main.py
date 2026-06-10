import sys 
from PyQt6.QtWidgets import QApplication, QMainWindow

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Youtube Downloader")
window.show()

sys.exit(app.exec())