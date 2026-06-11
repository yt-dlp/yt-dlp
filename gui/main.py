import sys 
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QLabel
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt



# app is required to run the application and starts the event loop. TL;dr dont move it from the top.
app = QApplication(sys.argv)



# sets the window title, size and icon. 
window = QMainWindow()
window.resize(600, 600)
window.setWindowTitle("Youtube Downloader")
window.setWindowIcon(QIcon("assets/logo.svg"))

# Container  AND the layout.
container = QWidget()
layout = QVBoxLayout()
container.setLayout(layout)
window.setCentralWidget(container)

# Input field, which takes the youtube video URl.
input_field = QLineEdit()
input_field.setPlaceholderText("Enter the URL of the video you want to download as mp3")
layout.addWidget(input_field)


# Status bar at the bottom of the window, which shows the status of the application.
window.statusBar().showMessage("Ready") 
window.show()
sys.exit(app.exec())