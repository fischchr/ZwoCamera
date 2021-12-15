from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi
from PyQt5.QtGui import QImage, QPicture, QPixmap
import time
import sys
import numpy as np
from multiprocessing import Process, Queue
from zwoasi import init, Camera, list_cameras, ASI_EXPOSURE, ASI_HIGH_SPEED_MODE, ASI_IMG_RAW8
from PIL import Image


class ZwoMini(Camera):
    def __init__(self):
        # Load the DLL
        self.load_lib()

        # Initialize the camera
        super(ZwoMini, self).__init__('ZWO ASI120MM Mini')
        
        
    def load_lib(self):
        """Initialize the camera. """

        init('libASICamera2.so')

    def set_exposure_time(self, exp_time: float):
        """Set the exposuer time (in seconds). """

        # Calculate the exposure time in us
        exp_time_us = int(exp_time * 1e6)
        # Set the exposure time
        self.set_control_value(ASI_EXPOSURE, exp_time_us)

    def enable_highspeed_mode(self):
        self.set_control_value(ASI_HIGH_SPEED_MODE, 1)

    def disable_highspeed_mode(self):
        self.set_control_value(ASI_HIGH_SPEED_MODE, 0)
          

class MainWindow(QMainWindow):
    def __init__(self):
        """Constructor for main window. """
        # Call constructor of parent object
        super(MainWindow, self).__init__()

        # Initialize the camera
        self.camera = ZwoMini()

        # Load gui
        loadUi('qt-gui/simple.ui', self)  

        # Take one picture
        self.camera.set_roi(0, 0, 1280, 960)
        self.camera.set_exposure_time(0.5e-3)
        img_data = self.camera.capture()

        # Display the picture
        self.display_image(img_data) 

    def display_image(self, image_data):
        # Convert image to 8 bit grayscale
        pil_image = Image.fromarray(image_data, 'L')
        # Get image size
        w, h = pil_image.size

        # Get byte representation
        byte_data = pil_image.tobytes("raw", "L")
        # Generate QImage object
        qimage = QImage(byte_data, w, h, QImage.Format_Grayscale8)
        # Transform it to QPixmap object
        qpixmap = QPixmap.fromImage(qimage)
        # Display the image
        self.imageLabel.setPixmap(qpixmap)
  


  
    def closeEvent(self, event):
        """Terminate all processes and threads when the main window is closed. """

        pass


if __name__ == '__main__':
    # Initialize app
    app = QApplication(sys.argv)
    # Initialize window
    main = MainWindow()
    # Show window
    main.show()
    # Start app
    sys.exit(app.exec_())  