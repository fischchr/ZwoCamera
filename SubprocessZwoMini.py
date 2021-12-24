from zwoasi import init, Camera, ASI_EXPOSURE, ASI_HIGH_SPEED_MODE, ASI_IMG_RAW8, ASI_COOLER_ON, ASI_FAN_ON, ASI_TEMPERATURE, ASI_TARGET_TEMP, ASI_IMG_RAW16
from Subprocess import Subprocess, Interface
from SubprocessHeader import *
from multiprocessing import Queue
from PyQt5.QtGui import QImage, QPixmap
from PIL  import Image
import time


def roi_absolute_to_swh(roi_x_1, roi_x_2, roi_y_1, roi_y_2):
    start_x = roi_x_1
    width = abs(roi_x_2 - roi_x_1)
    start_y = roi_y_1
    height = abs(roi_y_2 - roi_y_1)

    return start_x, start_y, width, height

def roi_swh_to_absolute(start_x, start_y, width, height):
    roi_x_1 = start_x
    roi_x_2 = roi_x_1 + width
    roi_y_1 = start_y
    roi_y_2 = roi_y_1 + height

    return roi_x_1, roi_x_2, roi_y_1, roi_y_2

def roi_absolute_to_offset(roi_x_1, roi_x_2, roi_y_1, roi_y_2, sensor_w, sensor_h):
    roi_width = roi_x_2 - roi_x_1
    offset_x = roi_x_1 - int(sensor_w / 2) + int(roi_width / 2)
    roi_height = roi_y_2 - roi_y_1
    offset_y = int(sensor_h / 2) - int(roi_height / 2) - roi_y_1
    

    return offset_x, roi_width, offset_y, roi_height

def roi_offset_to_absolute(offset_x, roi_width, offset_y, roi_height, sensor_w, sensor_h):
    roi_x_1 = int(sensor_w / 2) - int(roi_width / 2) + offset_x
    roi_x_2 = roi_x_1 + roi_width
    roi_y_1 = int(sensor_h / 2) - int(roi_height / 2) - offset_y
    roi_y_2 = roi_y_1 + roi_height

    return roi_x_1, roi_x_2, roi_y_1, roi_y_2

a = (0, 64, 0, 960)
b = roi_offset_to_absolute(*a, 1280, 960)
#print(b)
c = roi_absolute_to_swh(*b)
#print(c)
d = roi_swh_to_absolute(*c)
e = roi_absolute_to_offset(*d, 1280, 960)

assert a == e


class ZwoCamera(Camera):
    """Extension of zwoasi.Camera class. """

    def __init__(self, camera_name: str):
        # Load the DLL
        self.load_lib()

        # Initialize the camera
        super(ZwoCamera, self).__init__(camera_name)

        self._exp_time = None
        self._highspeed = False
        
    def load_lib(self):
        """Initialize the camera. """

        init('libASICamera2.so')

    @property
    def exp_time(self) -> float:
        """Get the exposure time (in seconds). """

        self._exp_time = self.get_control_value(ASI_EXPOSURE)[0] * 1e-6
        logging.debug(f'{self} read out exposure time of {self._exp_time * 1e6} us')
        return self._exp_time

    @exp_time.setter
    def exp_time(self, exp_time: float):
        """Set the exposuer time (in seconds). """

        # Calculate the exposure time in us
        exp_time_us = int(exp_time * 1e6)
        # Set the exposure time
        logging.debug(f'{self} set exposure time to {exp_time_us} us')
        self.set_control_value(ASI_EXPOSURE, exp_time_us)
        
    @property
    def highspeed(self) -> bool:
        """Get whether highspeed mode is enabled. """

        self._highspeed = self.get_control_value(ASI_HIGH_SPEED_MODE) * 1e-6
        return self._highspeed

    @highspeed.setter
    def highspeed(self, highspeed: bool):
        """Enable/disable highspeed mode. """

        self.set_control_value(ASI_HIGH_SPEED_MODE, bool(highspeed))

    @property
    def is_cooled(self):
        return self.get_camera_property()['IsCoolerCam']

    def enable_cooler(self):
        if self.is_cooled:
            self.set_control_value(ASI_COOLER_ON, 1)
            self.set_control_value(ASI_FAN_ON, 1)
            logging.debug(f'{self}: Enabeling cooler')
        else:
            logging.info(f'{self} is not cooled')

    def disable_cooler(self):
        if self.is_cooled:
            self.set_control_value(ASI_COOLER_ON, 0)
            self.set_control_value(ASI_FAN_ON, 0)
            logging.debug(f'{self}: Disabeling cooler')
        else:
            logging.info(f'{self} is not cooled')

    @property
    def temperature(self):
        if self.is_cooled:
            # Get the temperature (x10)
            t = self.get_control_value(ASI_TEMPERATURE)[0]
            logging.debug(f'Getting temperature')
            return t / 10
        else:
            logging.info(f'{self} is not cooled')

    @temperature.setter
    def temperature(self, t: float):
        if self.is_cooled:
            assert t > -40 and t < 20, 'Temperature out of range'
            self.set_control_value(ASI_TARGET_TEMP, t)
            logging.debug(f'Setting temperature to {t}')
        else:
            logging.info(f'{self} is not cooled')



class CameraSubprocess(Subprocess):
    """Implentation of a subprocess for running the ZWO mini camera. """
    def __init__(self, uid: int, camera_type: str, com_queue: Queue, res_queue: Queue):
        """Camera type: ZWO ASI120MM Mini or ZWO ASI174MM-Cool"""
        super().__init__(uid, com_queue, res_queue)

        self._camera_type = camera_type

        self._sensor_w = None
        self._sensor_h = None

        self._mode = None

    
    def run(self):
        """Extend the event loop of subprocess. """
        
        # Set camera
        self.camera = ZwoCamera(self._camera_type)

        info = self.camera.get_camera_property()
        self._sensor_w = info['MaxWidth']
        self._sensor_h = info['MaxHeight']

        self.camera.set_roi(0, 0, self._sensor_w, self._sensor_h, image_type=ASI_IMG_RAW8)
        self.camera.exp_time = 1e-3
        self.camera.highspeed = True
        if self.camera.is_cooled:
            self.camera.enable_cooler()
            self.camera.temperature = 0

        # Enable video mode
        self.camera.start_video_capture()

        # Run the subprocess event loop
        super(CameraSubprocess, self).run()

        # Stop video mode
        self.camera.stop_video_capture()
        self.camera.highspeed = False


    def inloop(self):
        """Add a function call in the event loop to read out the camera. """
        
        if self._mode == CMD_CAMERA_REC_MODE:
            img_data = []
            for i in range(1000):
                img_data.append(self.camera.capture_video_frame())
            # Update GUI
            self.send((CMD_DISPLAY_IMAGE, img_data[-1]))    
            # Return Image stack
            self.send((CMD_RETURN_REC, img_data))    
        elif self._mode == CMD_CAMERA_CONTINOUS_MODE:
            img_data = self.camera.capture_video_frame()
            self.send((CMD_DISPLAY_IMAGE, img_data))

    def handle_input(self, res):
        """Overwrite the function that handles commands from the main process. """

        if res[0] == CMD_CAMERA_GET_EXP:
            self.get_exposure_time()
        elif res[0] == CMD_CAMERA_SET_EXP:
            self.set_exposure_time(res[1])
        elif res[0] == CMD_CAMERA_MODE_STOP:
            # Set camera mode to not recording
            self._mode = CMD_CAMERA_MODE_STOP
        elif res[0] == CMD_CAMERA_CONTINOUS_MODE:
            # Set camera mode to continusous
            self._mode = CMD_CAMERA_CONTINOUS_MODE
        elif res[0] == CMD_CAMERA_REC_MODE:
            # Set camera mode to recording
            self._mode = CMD_CAMERA_REC_MODE   
        elif res[0] == CMD_CAMERA_GET_ROI:
            self.get_roi()
        elif res[0] == CMD_CAMERA_SET_ROI:
            self.set_roi(*res[1])
        elif res[0] == CMD_CAMERA_GET_TEMP:
            raise NotImplementedError
        elif res[0] == CMD_CAMERA_SET_TEMP:
            raise NotImplementedError

        
    def get_exposure_time(self):
        """Get the exposure time from the camera and put the result on the res_queue. """

        logging.debug(f'{self} reads out exposure time.')
        data = [CMD_CAMERA_GET_EXP, self.camera.exp_time]
        self.send(data)

    def set_exposure_time(self, val: float):
        """Set the exposure time (in seconds) and send the actual set value back. """
        
        logging.debug(f'{self} sets exposure time.')
        #self.camera.stop_video_capture()
        self.camera.exp_time = val

        self.get_exposure_time()

    def get_roi(self):
        """Get the ROI and trigger updating of the GUI.
        
        # Returns
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        * sensor_w::int - Width of the camera sensor.
        * sensor_h::int - Height of the camera sensor.
        """

        # Get the ROI from the camera
        start_x, start_y, width, height = self.camera.get_roi()

        # Calculate the absolute ROI
        roi_x_1, roi_x_2, roi_y_1, roi_y_2 = roi_swh_to_absolute(start_x, start_y, width, height)

        # Calculate the values we display in the GUI
        offset_x, roi_width, offset_y, roi_height = roi_absolute_to_offset(roi_x_1, roi_x_2, roi_y_1, roi_y_2, self._sensor_w, self._sensor_h)

        # Log values
        logging.info(f'{self} get ROI x: ({roi_x_1}, {roi_x_2}) y: ({roi_y_1}, {roi_y_2}).')
        logging.debug(f'ROI offset values x: ({offset_x}, {roi_width}) y: ({offset_y}, {roi_height}).')
        logging.debug(f'ROI swh values x: ({start_x}, {start_y}) y: ({width}, {height}).')

        # Return data
        data = [CMD_CAMERA_GET_ROI, (offset_x, roi_width, offset_y, roi_height, self._sensor_w, self._sensor_h)]
        self.send(data)

        #return offset_x, roi_width, offset_y, roi_height

    def set_roi(self, offset_x, roi_width, offset_y, roi_height):
        """Set the ROI.
        
        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        """

        # Calculate the absolute size of the ROI
        roi_x_1, roi_x_2, roi_y_1, roi_y_2 = roi_offset_to_absolute(offset_x, roi_width, offset_y, roi_height, self._sensor_w, self._sensor_h)

        # Check the size
        assert roi_x_1 >= 0 and roi_x_1 <= self._sensor_w, 'roi_x_1 out of range.'
        assert roi_x_2 >= 0 and roi_x_2 <= self._sensor_w, 'roi_x_2 out of range.'
        assert roi_y_1 >= 0 and roi_y_1 <= self._sensor_h, 'roi_y_1 out of range.'
        assert roi_y_2 >= 0 and roi_y_2 <= self._sensor_h, 'roi_y_2 out of range.'

        # Calculate the width and height of the ROI
        start_x, start_y, width, height = roi_absolute_to_swh(roi_x_1, roi_x_2, roi_y_1, roi_y_2)

        # Log values
        logging.info(f'{self} set ROI to x: ({roi_x_1}, {roi_x_2}) y: ({roi_y_1}, {roi_y_2}).')
        logging.debug(f'ROI offset values x: ({offset_x}, {roi_width}) y: ({offset_y}, {roi_height}).')
        logging.debug(f'ROI swh values x: ({start_x}, {start_y}) y: ({width}, {height}).')

        # Stop video recording to prevent crash
        self.camera.stop_video_capture()
        # Update ROI
        self.camera.set_roi(start_x, start_y, width, height, image_type=ASI_IMG_RAW8)
        # Continue recording
        self.camera.start_video_capture()

    def get_sensor_size(self):
        return (self._sensor_w, self._sensor_h)


class CameraInterface(Interface):
    def __init__(self, camera_type, image_label, res_queue: Queue, settings_window, streaming_button, rec_button, settings_button):
        """Constructor. camera_type: ZWO ASI120MM Mini or ZWO ASI174MM-Cool"""

        if camera_type == 'ZWO ASI120MM Mini':
            ID = CAMERA_ID
        elif camera_type == 'ZWO ASI174MM-Cool':
            ID = COOL_CAMERA_ID
        else:
            raise NotImplementedError(f'{camera_type} not known.')

        super().__init__(ID, res_queue)

        # Initialize GUI elements for controling the camera

        # Initialize the GUI element for displaying the camera image
        self.image_label = image_label
        self.streaming_button = streaming_button
        self.recording_button = rec_button
        self.settings_button = settings_button

        # Settings window
        self.settings_window = settings_window
        self.settings_window.connect_signals(self.set_exp_time, self.set_roi)

        # Signals
        self.streaming_button.clicked.connect(self.toggle_streaming_mode)
        self.recording_button.clicked.connect(self.toggle_recording_mode)     
        self.settings_button.clicked.connect(self.toggle_settings) 

        # Camera time
        self._camera_type = camera_type

        # Camera state
        self._camera_state = None

    def toggle_streaming_mode(self):
        if self._camera_state == CMD_CAMERA_MODE_STOP or self._camera_state == CMD_CAMERA_REC_MODE:
            self.set_continuous_mode()
        else:
            self.stop_recording()

    def toggle_recording_mode(self):
        if self._camera_state == CMD_CAMERA_MODE_STOP or self._camera_state == CMD_CAMERA_CONTINOUS_MODE:
            self.set_rec_mode()
        else:
            self.stop_recording()

    def toggle_settings(self):
        if not self.settings_window.isVisible():
            self.settings_window.show()

    def load_camera_settings(self):
        self.get_exp_time()
        self.get_roi()

    def init_subprocess(self):
        """Overwrite the parent function for initializing the subprocess. """

        return CameraSubprocess(self.uid, self._camera_type, self.com_queue, self.res_queue)

    def handle_data(self, data):
        """Handle data sent back from the camera subprocess. """

        cmd = data[0]

        if cmd == CMD_DISPLAY_IMAGE:
            self.display_image(data[1])
        elif cmd == CMD_CAMERA_GET_EXP:
            self.display_exp_time(data[1])
        elif cmd == CMD_CAMERA_GET_ROI:
            self.update_roi(*data[1])

    def display_image(self, image_data):
        """Display an image. """

        # Convert image to 8 bit grayscale
        pil_image = Image.fromarray(image_data, 'L')
        # Get image size
        w, h = pil_image.size

        # Get the aspect ratio
        #(_, roi_w, _, roi_h) = self.settings_window.get_roi_values()

        # Get the size of the output
        output_w = 640
        output_h = 480 #int(640 * roi_h / roi_w)
        #print(roi_h, roi_w, output_h)

        pil_image = pil_image.resize((output_w, output_h))
        w, h = pil_image.size
        #print(w, h)

        # Get byte representation
        byte_data = pil_image.tobytes("raw", "L")
        # Generate QImage object
        qimage = QImage(byte_data, output_w, output_h, QImage.Format_Grayscale8)
        # Transform it to QPixmap object
        qpixmap = QPixmap.fromImage(qimage)
        # Display the image
        self.image_label.setPixmap(qpixmap)

    def display_exp_time(self, val):
        """Display the exposure time in the GUI. """

        logging.debug(f'{self} received exposure {val * 1e6} us from {self.subprocess}.')
        self.settings_window.set_exp_time(val)

    def update_roi(self, offset_x, roi_width, offset_y, roi_height, sensor_w, sensor_h):
        """Update the GUI with current ROI values.
        
        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        * sensor_w::int - Width of the camera sensor.
        * sensor_h::int - Height of the camera sensor.
        """
        
        # Log values
        logging.debug(f'{self} updates ROI to {offset_x}, {roi_width}, {offset_y}, {roi_height}.')


        # Update GUI
        self.settings_window.set_roi_values(offset_x, roi_width, offset_y, roi_height, sensor_w, sensor_h)
        

    def get_exp_time(self):
        """Query the exposure time from the subprocess. """

        logging.debug(f'{self} querying exposure time.')
        self.com_queue.put((CMD_CAMERA_GET_EXP, ))

    def set_exp_time(self):
        """Set the exposure time of the camera. """

        try:
            exp_time = self.settings_window.get_exp_time()
            logging.debug(f'{self} setting exposure time to {exp_time * 1e6} us.')
            self.com_queue.put((CMD_CAMERA_SET_EXP, exp_time))
        except ValueError as e:
            logging.info(f'{e}')
    
    def set_roi(self):
        """Set the ROI. 

        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        """
        try:
            roi = self.settings_window.get_roi_values()
            #print(roi)

            self.com_queue.put((CMD_CAMERA_SET_ROI, roi))
        except AssertionError as e:
            print(e)

        self.get_roi()

    def get_roi(self):
        """Get the ROI. """

        logging.debug(f'{self} getting ROI')
        self.com_queue.put((CMD_CAMERA_GET_ROI, ))

    def stop_recording(self):
        logging.info('Stopping all recording')

        # Stop camera
        self._camera_state = CMD_CAMERA_MODE_STOP
        self._update_state()

        # Reset buttons
        self.streaming_button.setText('Start Stream')
        self.recording_button.setText('Start Recording')
        
    def set_continuous_mode(self):

        logging.info('Starting continuous video streaming')

        # Start streaming
        self._camera_state = CMD_CAMERA_CONTINOUS_MODE
        self._update_state()

        # Set buttons
        self.streaming_button.setText('Stop Stream')
        self.recording_button.setText('Start Recording')

    def set_rec_mode(self):

        logging.info('Starting recording')

        # Start recording
        self._camera_state = CMD_CAMERA_REC_MODE
        self._update_state()

        # Set buttons
        self.StreamingButton.setText('Start Stream')
        self.RecordingButton.setText('Stop Recording')


    def _update_state(self):
        self.com_queue.put((self._camera_state, ))
