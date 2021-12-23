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
    offset_y = roi_y_1 - int(sensor_h / 2) + int(roi_height / 2)
    

    return offset_x, roi_width, offset_y, roi_height

def roi_offset_to_absolute(offset_x, roi_width, offset_y, roi_height, sensor_w, sensor_h):
    roi_x_1 = int(sensor_w / 2) - int(roi_width / 2) + offset_x
    roi_x_2 = roi_x_1 + roi_width
    roi_y_1 = int(sensor_h / 2) - int(roi_height / 2) + offset_y
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

        self._mode = None
        self._camera_type = camera_type
    
    def run(self):
        """Extend the event loop of subprocess. """

        # Initialize the camera
        self.camera = ZwoCamera(self._camera_type)

        self.camera.set_roi(0, 0, 1280, 960, image_type=ASI_IMG_RAW8)
        self.camera.exp_time = 1e-3
        self.camera.highspeed = False
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
        """

        # Get the sensor size
        sensor_w = 1280
        sensor_h = 960

        # Get the ROI from the camera
        start_x, start_y, width, height = self.camera.get_roi()

        # Calculate the absolute ROI
        roi_x_1, roi_x_2, roi_y_1, roi_y_2 = roi_swh_to_absolute(start_x, start_y, width, height)

        # Calculate the values we display in the GUI
        offset_x, roi_width, offset_y, roi_height = roi_absolute_to_offset(roi_x_1, roi_x_2, roi_y_1, roi_y_2, sensor_w, sensor_h)

        # Log values
        logging.info(f'{self} get ROI x: ({roi_x_1}, {roi_x_2}) y: ({roi_y_1}, {roi_y_2}).')
        logging.debug(f'ROI offset values x: ({offset_x}, {roi_width}) y: ({offset_y}, {roi_height}).')
        logging.debug(f'ROI swh values x: ({start_x}, {start_y}) y: ({width}, {height}).')

        # Return data
        data = [CMD_CAMERA_GET_ROI, (offset_x, roi_width, offset_y, roi_height)]
        self.send(data)

        return offset_x, roi_width, offset_y, roi_height

    def set_roi(self, offset_x, roi_width, offset_y, roi_height):
        """Set the ROI.
        
        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        """

        # Get the size of the sensor
        sensor_w = 1280
        sensor_h = 960

        # Calculate the absolute size of the ROI
        roi_x_1, roi_x_2, roi_y_1, roi_y_2 = roi_offset_to_absolute(offset_x, roi_width, offset_y, roi_height, sensor_w, sensor_h)

        # Check the size
        assert roi_x_1 >= 0 and roi_x_1 <= sensor_w, 'roi_x_1 out of range.'
        assert roi_x_2 >= 0 and roi_x_2 <= sensor_w, 'roi_x_2 out of range.'
        assert roi_y_1 >= 0 and roi_y_1 <= sensor_h, 'roi_y_1 out of range.'
        assert roi_y_2 >= 0 and roi_y_2 <= sensor_h, 'roi_y_2 out of range.'

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


class CameraInterface(Interface):
    def __init__(self, camera_type, image_label, exp_time_input, res_queue: Queue, roi_inputs: list):
        """Constructor. camera_type: ZWO ASI120MM Mini or ZWO ASI174MM-Cool"""

        super().__init__(CAMERA_ID, res_queue)

        # Initialize GUI elements for controling the camera
        self.exp_time_input = exp_time_input

        # Initialize the GUI element for displaying the camera image
        self.image_label = image_label

        # ROI inputs
        self.roi_inputs = roi_inputs

        self._camera_type = camera_type

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

        # Get byte representation
        byte_data = pil_image.tobytes("raw", "L")
        # Generate QImage object
        qimage = QImage(byte_data, w, h, QImage.Format_Grayscale8)
        # Transform it to QPixmap object
        qpixmap = QPixmap.fromImage(qimage)
        # Display the image
        self.image_label.setPixmap(qpixmap)

    def display_exp_time(self, val):
        """Display the exposure time in the GUI. """

        logging.debug(f'{self} received exposure {val * 1e6} us from {self.subprocess}.')
        self.exp_time_input.setText(str(val))

    def update_roi(self, offset_x, roi_width, offset_y, roi_height):
        """Update the GUI with current ROI values.
        
        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        """
        
        # Log values
        logging.debug(f'{self} updates ROI to {offset_x}, {roi_width}, {offset_y}, {roi_height}.')

        # Update GUI
        self.roi_inputs[0].setValue(offset_x)
        self.roi_inputs[1].setValue(roi_width)
        self.roi_inputs[2].setValue(offset_y)
        self.roi_inputs[3].setValue(roi_height)

    def get_exp_time(self):
        """Query the exposure time from the subprocess. """

        logging.debug(f'{self} querying exposure time.')
        self.com_queue.put((CMD_CAMERA_GET_EXP, ))

    def set_exp_time(self, val):
        """Set the exposure time of the camera. """

        logging.debug(f'{self} setting exposure time to {val * 1e6} us.')
        self.com_queue.put((CMD_CAMERA_SET_EXP, val))
    
    def set_roi(self, offset_x, roi_width, offset_y, roi_height):
        """Set the ROI. 

        # Arguments
        * offset_x::int - Offset from the sensor center in x.
        * roi_width::int -  Width of the ROI.
        * offset_y::int - Offset from the sensor center in y.
        * roi_height::int - Height of the ROI.
        """

        roi = (offset_x, roi_width, offset_y, roi_height)

        self.com_queue.put((CMD_CAMERA_SET_ROI, roi))

    def get_roi(self):
        """Get the ROI. """

        logging.debug(f'{self} getting ROI')
        self.com_queue.put((CMD_CAMERA_GET_ROI, ))

    def stop_recording(self):
        self.com_queue.put((CMD_CAMERA_MODE_STOP, ))

    def set_continuous_mode(self):
        self.com_queue.put((CMD_CAMERA_CONTINOUS_MODE, ))

    def set_rec_mode(self):
        self.com_queue.put((CMD_CAMERA_REC_MODE, ))