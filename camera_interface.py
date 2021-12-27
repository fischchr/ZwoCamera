from multiprocessing import process
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi
#from PyQt5.QtGui import QImage, QPicture, QPixmap
import time
import sys
import numpy as np
from camera_settings import CameraSettingsWindow
#from ASICamera.testing.Subprocess import InterfaceManager



from Subprocess import *
from SubprocessHeader import *
from SubprocessZwoMini import *

import logging
logging.basicConfig(filename='camera.log', level=logging.DEBUG)



class CommunicationWorker(QObject):
    # Signal for starting the communication thread. Required by Qt
    start_communication_signal = pyqtSignal()

    def __init__(self, res_queue: Queue, interface_manager: InterfaceManager):
        """Constructor of the communication thread. 
        
        # Arguments
        * counterLabel1::QLabel - Label for displaying the value of counter 1.
        * counterLabel2::QLabel - Label for displaying the value of counter 2.
        * com_queue1::Queue - Communication queue for stopping counter1.
        * com_queue2::Queue - Communication queue for stopping counter2.
        * res_queue::Queue - Communication queue for getting back the counter values.
        """

        # Call constructor of parent object
        super(CommunicationWorker, self).__init__()

        # Store the result queue
        self.res_queue = res_queue

        # Store the command queues for both counters
        self.interface_manager = interface_manager
        #self.camera_interface = camera_interface
        
        # Connect start signal for starting the thread
        self.start_communication_signal.connect(self.run_thread)

        # Set state
        self.running = False

    @pyqtSlot()
    def run_thread(self):
        """Code that runs when the subprocess is started. """

        # Start thread
        logging.info(f'Starting event loop of {self}')
        self.running = True

        while self.running:
            # Check for results
            if not self.res_queue.empty():
                # Get data sent back from subprocess
                uid, data = self.res_queue.get()
                # Handle the data correctly
                self.interface_manager[uid].handle_data(data)
            else:
                # Idle
                time.sleep(0.01)

        logging.info(f'Stopped event loop of {self}')
            
    def stop_thread(self):
        """Function that is called to stop the communication thread. """

        self.running = False
  

class MainWindow(QMainWindow):
    def __init__(self):
        """Constructor for main window. """

        # Call constructor of parent object
        super(MainWindow, self).__init__()


        ### Initialize GUI ###
        # Load gui of the main window
        loadUi('qt-gui/simple.ui', self)  

        star_camera_name = 'ZWO ASI120MM Mini'
        science_camera_name = 'ZWO ASI174MM-Cool'

        # Initialize all windows
        self.asi_mini_settings = CameraSettingsWindow(f'Settings {star_camera_name}')
        self.asi_cool_settings = CameraSettingsWindow(f'Settings {science_camera_name}')


        ### Initialize subprocesses ###
        # Create result queue which is shared by all subprocesses
        self.res_queue = Queue()

        # Initialize the camera interfaces
        self.mini_camera_interface = CameraInterface(star_camera_name, self.imageLabelMini, self.res_queue, self.asi_mini_settings, self.miniStreamingButton, self.miniRecordingButton, self.miniSettingsButton)
        self.cool_camera_interface = CameraInterface(science_camera_name, self.imageLabelCool, self.res_queue, self.asi_cool_settings, self.coolStreamingButton, self.coolRecordingButton, self.coolSettingsButton)

        # Create the interface manager
        self.interface_manager = InterfaceManager(self.mini_camera_interface, self.cool_camera_interface)


        ### Initialize the communication between the main window and the subprocesses ###
        # Create the communication worker
        self.communication_worker = CommunicationWorker(self.res_queue, self.interface_manager)

        # Create a new thread for the communicaiton worker
        self.communication_thread = QThread(self)
        # Move the communicaiton worker to the new thread
        self.communication_worker.moveToThread(self.communication_thread)
        # Start the thread
        self.communication_thread.start()
        # Start the communication worker
        self.communication_worker.start_communication_signal.emit()


        ### Start subprocesses ###
        # Start Mini camera process
        self.start_subprocess(CAMERA_ID)
        self.mini_camera_interface.load_camera_settings()
        self.mini_camera_interface.stop_recording()

        # Start Cool camera process
        self.start_subprocess(COOL_CAMERA_ID)
        self.cool_camera_interface.load_camera_settings()
        self.cool_camera_interface.stop_recording()


    ### Handling starting and stopping of subprocesses ###
    def start_subprocess(self, uid: int):
        """Start a subprocess. """
        self.interface_manager[uid].start_subprocess()
 
    def stop_subprocess(self, uid):
        """Stop a subprocess. """
        self.interface_manager[uid].start_subprocess()

    def closeEvent(self, event):
        """Terminate all processes and threads when the main window is closed. """

        # Stop all subprocesses
        for interface in self.interface_manager:
            interface.stop_subprocess()

        # Close all windows
        self.asi_mini_settings.close()
        self.asi_cool_settings.close()

        # Stop the communication worker
        self.communication_worker.stop_thread()
        # Stop the thread we spawned for the communication worker
        self.communication_thread.quit()
        # Wait for it to fully terminate
        self.communication_thread.wait()


if __name__ == '__main__':
    # Initialize app
    app = QApplication(sys.argv)
    # Initialize window
    main = MainWindow()
    # Show window
    main.show()
    # Start app
    sys.exit(app.exec_())  