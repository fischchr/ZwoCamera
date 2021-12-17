from multiprocessing import process
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi
#from PyQt5.QtGui import QImage, QPicture, QPixmap
import time
import sys
import numpy as np
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
        # Load gui
        loadUi('qt-gui/simple.ui', self)  

        # Connect elements to functions
        self.exp_time_input.editingFinished.connect(self.set_exp_time)
        self.StreamingButton.clicked.connect(self.toggle_streaming_mode)
        self.RecordingButton.clicked.connect(self.toggle_recording_mode)


        ### Initialize subprocesses ###
        # Create result queue which is shared by all subprocesses
        self.res_queue = Queue()

        # Initialize the camera interface
        self.camera_interface = CameraInterface(self.imageLabel, self.exp_time_input, self.res_queue)

        # Create the interface manager
        self.interface_manager = InterfaceManager(self.camera_interface)

        
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
        # Start camera process
        self.start_subprocess(CAMERA_ID)
        self.get_exp_time()
        self.set_camera_not_recording()


    ### GUI functions for controlling the camera
    def get_exp_time(self):
        """Get the exposure time from the camera. """

        self.interface_manager[CAMERA_ID].get_exp_time()

    def set_exp_time(self):
        """Set the exposure time of the camera. """
        val = self.exp_time_input.text()
        try:
            val = float(val)
            if val > 2e-6 and val < 5:
                self.interface_manager[CAMERA_ID].set_exp_time(val)
        except ValueError:
            pass

    def toggle_streaming_mode(self):
        if self.camera_mode == CMD_CAMERA_MODE_STOP or self.camera_mode == CMD_CAMERA_REC_MODE:
            self.set_camera_continuous_mode()
        else:
            self.set_camera_not_recording()

    def toggle_recording_mode(self):
        if self.camera_mode == CMD_CAMERA_MODE_STOP or self.camera_mode == CMD_CAMERA_CONTINOUS_MODE:
            self.set_camera_rec_mode()
        else:
            self.set_camera_not_recording()


    def set_camera_not_recording(self):
        logging.info('Stopping all recording')
        # Stop camera
        self.camera_mode = CMD_CAMERA_MODE_STOP
        self.interface_manager[CAMERA_ID].stop_recording()
        # Reset buttons
        self.StreamingButton.setText('Start Stream')
        self.RecordingButton.setText('Start Recording')

    def set_camera_continuous_mode(self):
        logging.info('Starting continuous video streaming')
        # Start streaming
        self.camera_mode = CMD_CAMERA_CONTINOUS_MODE
        self.interface_manager[CAMERA_ID].set_continuous_mode()
        # Set buttons
        self.StreamingButton.setText('Stop Stream')
        self.RecordingButton.setText('Start Recording')

    def set_camera_rec_mode(self):
        logging.info('Starting recording')
        # Start recording
        self.camera_mode = CMD_CAMERA_REC_MODE
        self.interface_manager[CAMERA_ID].set_rec_mode()
        # Set buttons
        self.StreamingButton.setText('Start Stream')
        self.RecordingButton.setText('Stop Recording')


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