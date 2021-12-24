from multiprocessing import process
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5.uic import loadUi
#from PyQt5.QtGui import QImage, QPicture, QPixmap
import time
import sys
import numpy as np
import logging
#from ASICamera.testing.Subprocess import InterfaceManager

class CameraSettingsWindow(QWidget):
    def __init__(self):
        # Call constructor of parent object
        super(CameraSettingsWindow, self).__init__()

        # Load gui
        loadUi('qt-gui/camera_settings.ui', self) 

        self.exp_time_input = self.exp_time 

    def connect_signals(self, f_exp_time_change, f_roi_change):
        self.exp_time_input.editingFinished.connect(f_exp_time_change)

        self.offset_x_input.editingFinished.connect(f_roi_change)
        self.width_input.editingFinished.connect(f_roi_change)
        self.offset_y_input.editingFinished.connect(f_roi_change)
        self.height_input.editingFinished.connect(f_roi_change)

    def get_exp_time(self):

        exp_time = self.exp_time_input.value() / 1e3 # exp_time in seconds
        if exp_time > 2e-6 and exp_time < 5:
            return exp_time
        else:
            raise ValueError('exp_time out of range')

    def set_exp_time(self, exp_time):

        exp_time_ms = exp_time * 1e3
        self.exp_time_input.setValue(exp_time_ms)

    def get_roi_values(self):
        # Get inputs
        offset_x = self.offset_x_input.value()
        width = self.width_input.value()
        offset_y = self.offset_y_input.value()
        height = self.height_input.value()

        # Make sure width is divisible by 8
        roi_width = int(width / 8) * 8
        assert roi_width > 0, 'ROI width must be positive'

        # Make sure height is divisible by 2
        roi_height = int(height / 2) * 2
        assert roi_height > 0, 'ROI height must be positive'

        return offset_x, width, offset_y, height

    def set_roi_values(self, offset_x, width, offset_y, height, sensor_w, sensor_h):

        # Update the input limits
        self.set_roi_limits(offset_x, width, offset_y, height, sensor_w, sensor_h)

        self.offset_x_input.setValue(offset_x)
        self.width_input.setValue(width)
        self.offset_y_input.setValue(offset_y)
        self.height_input.setValue(height)

    def set_roi_limits(self, offset_x, width, offset_y, height, sensor_w, sensor_h):

        # ROI width 
        min_width = 88
        max_width = int((sensor_w - 2*abs(offset_x)) / 8) * 8

        self.width_input.setRange(min_width, max_width)
        self.width_input.setSingleStep(8)

        # ROI height
        min_height = 2
        max_height = int((sensor_h - 2*abs(offset_y)) / 2) * 2
        self.height_input.setRange(min_height, max_height)
        print(min_height, max_height)
        self.height_input.setSingleStep(2)

        # Offset x
        min_offset_x = int((width - sensor_w ) / 2)
        max_offset_x = int((sensor_w - width) / 2)
        if max_offset_x > 0:
            max_offset_x -= 1
        self.offset_x_input.setRange(min_offset_x, max_offset_x)
        self.offset_x_input.setSingleStep(1)

        # Offset y
        min_offset_y = int((height - sensor_h ) / 2)
        max_offset_y = int((sensor_h - height) / 2)
        if max_offset_y > 0:
            max_offset_y -= 1
        self.offset_y_input.setRange(min_offset_y, max_offset_y)
        self.offset_y_input.setSingleStep(1)


        # Log values
        logging.debug(f'{self} maximum size values x: ({min_width}, {max_width}) y: ({min_height}, {max_height})')
        logging.debug(f'{self} maximum offset values x: ({min_offset_x}, {max_offset_x}) y: ({min_offset_y}, {max_offset_y})')

        

        
        #self.offset_y_input.setRange(-999999, 999999)
        #self.offset_x_input.setRange(-int(sensor_w / 2), int(sensor_w / 2) - width)
        #self.offset_y_input.setRange(-int(sensor_h / 2), int(sensor_h / 2) - height)
