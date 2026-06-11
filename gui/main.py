import sys 
# GOT DAMN okay im using import * next time. i Cba adding every single import again.
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QProgressBar, QTextEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QProcess



#The syntax looks weird, because we need to instantiate alot of objects. This is a common pattern in PyQt applications, where you create various widgets and set up their properties and layout before starting the event loop.




# app is required to run the application and starts the event loop. TL;dr dont move it from the top.
# maby i should put it in a main function?
app = QApplication(sys.argv)


# sets the window title, size and icon. 
window = QMainWindow()
window.resize(400, 400)
window.setWindowTitle("Youtube Downloader")
window.setWindowIcon(QIcon("assets/logo.svg"))

# Container  AND the layout.
container = QWidget()
layout = QVBoxLayout()
container.setLayout(layout)
window.setCentralWidget(container)

# Input field, which takes the youtube video URL.
input_field = QLineEdit() 
input_field.setPlaceholderText("Enter the URL of the video you want to download as mp3")
layout.addWidget(input_field)


#instantiates the process object, which is used to run the yt-dlp command in a separate process. This allows the GUI to remain responsive while the download is in progress.
process = QProcess()

# The progress bar inside the function needs to exsist in the layout before the function runs... why..? idk...
# PROGRESS BAR is used to show the progress of the download. It will be updated based on the output of the yt-dlp process.
progress_bar = QProgressBar()
progress_bar.setValue(0)
layout.addWidget(progress_bar)


# this is the output box which showcase the yt-dlp output, normally you have the terminal to give you info if run the command.
# Here its added as text to the GUI. 
output_box = QTextEdit()
output_box.setReadOnly(True)
layout.addWidget(output_box)


#You need this to read the output of the process and update the progress bar accordingly.
# The output of yt-dlp contains the percentage of the download, so we can parse that and update the progress bar.


def progressError():
    output = process.readAllStandardError().data().decode()
    output_box.append(output)
    if "100%" in output:
        progress_bar.setValue(100)
    elif "%" in output:
        try:
            percentage = int(output.split("%")[0].split()[-1])
            progress_bar.setValue(percentage)
        except ValueError:
            print("Could not parse percentage from output")
            pass

process.readyReadStandardError.connect(progressError)





def download_function():
    url = input_field.text().strip()
    if url:
        # Start the download process using yt-dlp, Damn thats a cursed path.
        process.start(sys.executable, ["-m", "yt_dlp", "-x", "--audio-format", "mp3", "-o", "../downloads/%(title)s.%(ext)s", url])  
    else:
        print("Please enter a valid URL")  # You can also display this in the GUI if needed



button = QPushButton("Download")
button.clicked.connect(download_function)
layout.addWidget(button)



# Status bar at the bottom of the window, which shows the status of the application.
window.statusBar().showMessage("Ready") 
window.show()

# SystemExit(app.exec()) Stops the process off app.exec. app.exec() starts the event loop on the first line, which is necessary for the GUI to function. It waits for events (like button clicks) and updates the GUI accordingly. When the application is closed, app.exec() returns, and sys.exit(). note@ freddy: "This might be wrong, but its just my understanding of it."" 
sys.exit(app.exec())
