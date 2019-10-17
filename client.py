#!/usr/bin/env python3
 
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import sys
import os
import traceback
import json
import ctypes
from PIL import Image
from PyQt5.QtWidgets import QWidget, QLabel, QTextEdit
from PyQt5.QtWidgets import QGridLayout, QPushButton
from PyQt5.QtWidgets import QApplication, QDialog, QLineEdit
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal

# Define a bold font for headers
bold = QtGui.QFont("Times", 11, QtGui.QFont.Bold)

# Message modes
class MODE:
    setup = 'setup'
    message = 'message'
    escape = 'escape'
    image = 'image'


class ChatWindow(QWidget):
    def __init__(self, name=None):
        # Initialize QT Stuff
        super().__init__()

        # Window info
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        # Setup interface
        self.initUI()

        # Setup backend
        self.backend = ChatBackend(name)
        self.backend.message_signal.connect(self.new_message)
        self.backend.start()

        # Print welcome message
        self.text.append("Welcome to PyChat!")


    def closeEvent(self, event):
        ''' When the application is closing '''
        try: self.backend.quit() # Delete the backend and close socket
        except: pass
        event.accept() # Close


    def initUI(self):
        ## Setup Layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Large text edit field
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        grid.addWidget(self.text, *(0, 0))

        # Text entry
        submit = QPushButton('Send')
        submit.clicked.connect(self.send_pressed)
        grid.addWidget(submit, *(2, 0))
        self.entry = QLineEdit()
        self.entry.returnPressed.connect(self.send_pressed)
        grid.addWidget(self.entry, *(1, 0))

        # Image
        image_button = QPushButton("Image Send")
        image_button.clicked.connect(self.send_image)
        grid.addWidget(image_button, *(3, 0))

        ## Set window geometry and show
        self.setGeometry(100, 100, 400, 900)
        self.setWindowTitle('PyChat') 
        self.show()

        # Set focus to the message entry
        self.entry.setFocus()

    
    def new_message(self, message):
        ''' Add new received message to window '''
        self.text.append(message)
        QApplication.processEvents()  # Force gui refresh

        # Flash the window
        #ctypes.windll.user32.FlashWindow(ctypes.windll.kernel32.GetConsoleWindow(), True)

    
    def send_pressed(self):
        ''' Send the message '''
        # Get message
        message = self.entry.text()

        # Don't send if an empty message
        if(message == ""):
            return

        # Send on backend
        self.backend.send(MODE.message, message)

        # Clear entry field
        self.entry.clear()


    def send_image(self):
        ''' Send the image '''
        # Get the image path
        image_path = self.entry.text()

        # Check that image exists
        if(not os.path.exists(image_path)):
            self.text.append("Image path doesn't exit!")
            return

        # Tell backend to send image
        self.backend.send_image(image_path)

        # Clear entry field
        self.entry.clear()


class ChatLogin(QWidget):
    def __init__(self):
        # Initialize QT Stuff
        super().__init__()

        # Setup interface
        self.initUI()

    def initUI(self):
        ## Setup Layout
        grid = QGridLayout()
        self.setLayout(grid)

        # Label
        label = QLabel("Pleast enter your name")
        grid.addWidget(label, *(0, 0))

        # Text Entry
        self.entry = QLineEdit()
        self.entry.returnPressed.connect(self.login)
        grid.addWidget(self.entry, *(0, 1))

        # Login button
        button = QPushButton('Login')
        button.clicked.connect(self.login)
        grid.addWidget(button, *(1, 0), 1, 2)

        ## Set window geometry and show
        self.setWindowTitle('PyChat') 
        self.show()

    def login(self):
        # Log user in
        name = self.entry.text()

        self.cams = ChatWindow(name)
        self.cams.show()
        self.close()


class ChatBackend(QtCore.QThread):
    message_signal = pyqtSignal(str)
    def __init__(self, name, parent=None):
        ## Initialize QtThread
        QtCore.QThread.__init__(self, parent)

        # Define socket
        #HOST = input('Enter host: ')
        #PORT = input('Enter port: ')
        HOST = '141.199.9.64'
        PORT = 33000

        if(name):
            self.name = name
        else:
            self.name = input("Name: ")
        
        if not PORT:
            PORT = 33000 # Default value.
        else:
            PORT = int(PORT)
        self.BUFSIZ = 4096
        ADDR = (HOST, PORT)
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect(ADDR)

        self.send(MODE.setup, self.name)


    def quit(self):
        ''' On delete alert server '''
        print("exiting")
        self.send(MODE.escape)
        self.client_socket.close()


    def run(self):
        """Handles receiving of messages."""
        while True:
            try:
                # Get message from socket
                message_raw = self.client_socket.recv(self.BUFSIZ)

                if(message_raw == b''):
                    continue

                # Decode
                try:
                    message_data = json.loads(message_raw.decode('utf8'))
                except:
                    print("INVALID MESSAGE")
                    print(message_raw)

                # Conditionally handle the message
                message_mode = message_data.get('mode')
                message = message_data.get('data')
                message_sender = message_data.get('from')

                if(message_mode == MODE.message):
                    self.message_signal.emit(str(message_sender) + ": " + str(message))

                elif(message_mode == MODE.image):
                    # Get the image
                    length = message.get('length')
                    size = message.get('size')
                    self.message_signal.emit(f"Receiving image from {message_sender}")
                    image_data = self.client_socket.recv(length)

                    # Decode and display
                    image = Image.frombytes('RGBA', size, image_data)
                    image.show()

                else:
                    print("Invalid mode")
                    print(message_data)
            
            except OSError: # Possibly client has left the chat.
                print("backend quit")
                sys.exit()
        
            except:
                print(traceback.format_exc())
    

    def send(self, mode, message=''): # event is passed by binders.
        to_send = {
            'from':self.name,
            'mode':mode,
            'data':message
        }
        self.client_socket.send(json.dumps(to_send).encode('utf8') + b'({(')
        
        if mode == MODE.escape:
            self.client_socket.close()
            sys.exit()

    
    def send_image(self, image_path):
        # Open image
        image_obj = Image.open(image_path)
        image_data = image_obj.tobytes()
        image_length = len(image_data)
        image_size = image_obj.size
        data = {'length':image_length, 'size':image_size}

        # Send first message to prepare server for image
        self.send(MODE.image, data)

        # Send image
        self.client_socket.send(image_data)


if __name__ == '__main__':
    # Setup GUI
    app = QApplication(sys.argv)
    window = ChatLogin()

    # Run the GUI mainloop
    sys.exit(app.exec_())