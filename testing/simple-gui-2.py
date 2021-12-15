from multiprocessing import process
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi
from PyQt5.QtGui import QImage, QPicture, QPixmap
import time
import sys
import numpy as np



from Subprocess import *
from SubprocessHeader import *
from SubprocessZwoMini import *




class CommunicationWorker(QObject):
    # Signal for starting the communication thread. Required by Qt
    start_communication_signal = pyqtSignal()

    def __init__(self, res_queue: Queue, interface_manager: InterfaceManager):
    
    #res_queue: Queue, com_queue: Queue, imageLabel: QLabel):
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

        #self.imageLabel = imageLabel

        # Set state
        self.running = False

    @pyqtSlot()
    def run_thread(self):
        """Code that runs when the subprocess is started. """

        # Start thread
        self.running = True

        while self.running:
            # Check for results
            if not self.res_queue.empty():
                uid, data = self.res_queue.get()
                self.interface_manager[uid].handle_data(data)

            else:
                # Idle
                time.sleep(0.01)
            
    def stop_thread(self):
        """Function that is called to stop the communication thread. """

        self.running = False

          

class MainWindow(QMainWindow):
    def __init__(self):
        """Constructor for main window. """
        # Call constructor of parent object
        super(MainWindow, self).__init__()

        # Load gui
        loadUi('qt-gui/simple.ui', self)  

        # Create result queue which is shared by all subprocesses
        self.res_queue = Queue()

        # Initialize the camera
        self.camera_queue = Queue()
        self.camera_process = None
        self.camera_interface = CameraInterface(self.imageLabel, self.exp_time_input, self.camera_queue, self.res_queue)

        # Create the interface manager
        self.interface_manager = InterfaceManager(self.camera_interface)

        # Create the process manager
        self.process_manager = ProcessManager()


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


        self.exp_time_input.editingFinished.connect(self.set_exp_time)

        # Start camera process
        self.start_subprocess(CAMERA_ID)
        self.get_exp_time()


    def start_subprocess(self, uid):
        if uid == CAMERA_ID:
            process = CameraSubprocess(self.camera_queue, self.res_queue)

        self.process_manager.start_subprocess(process)

  
    def stop_subprocess(self, uid):
        self.process_manager.stop_subprocess(uid)


    def get_exp_time(self):
        self.interface_manager[CAMERA_ID].get_exp_time()

    def set_exp_time(self):
        val = self.exp_time_input.text()
        try:
            val = float(val)
            if val > 2e-6 and val < 5:
                self.interface_manager[CAMERA_ID].set_exp_time(val)
        except ValueError:
            pass

        self.get_exp_time()

        
        #self.interface_manager[CAMERA_ID].set_exp_time(val)


  
    def closeEvent(self, event):
        """Terminate all processes and threads when the main window is closed. """

        # Stop all subprocesses
        #self.stop_subprocess(CAMERA_ID)
        self.process_manager.stop_all_subprocesses()

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