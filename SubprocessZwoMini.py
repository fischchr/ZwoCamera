from zwoasi import init, Camera, ASI_EXPOSURE, ASI_HIGH_SPEED_MODE, ASI_IMG_RAW8
from Subprocess import Subprocess, Interface
from SubprocessHeader import *
from multiprocessing import Queue
from PyQt5.QtGui import QImage, QPixmap
from PIL  import Image

class ZwoMini(Camera):
    """Extension of zwoasi.Camera class. """

    def __init__(self):
        # Load the DLL
        self.load_lib()

        # Initialize the camera
        super(ZwoMini, self).__init__('ZWO ASI120MM Mini')

        # 
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


class CameraSubprocess(Subprocess):
    """Implentation of a subprocess for running the ZWO mini camera. """
    def __init__(self, uid: int, com_queue: Queue, res_queue: Queue):
        super().__init__(uid, com_queue, res_queue)

        self._mode = None

    def run(self):
        """Extend the event loop of subprocess. """

        # Initialize the camera
        self.camera = ZwoMini()
        self.camera.set_roi(0, 0, 1280, 960, image_type=ASI_IMG_RAW8)
        self.camera.exposure_time = 1e-3
        self.camera.highspeed = True

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
            for i in range(100):
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
        
    def get_exposure_time(self):
        """Get the exposure time from the camera and put the result on the res_queue. """

        logging.debug(f'{self} reads out exposure time.')
        data = [CMD_CAMERA_GET_EXP, self.camera.exp_time]
        self.send(data)

    def set_exposure_time(self, val: float):
        """Set the exposure time (in seconds) and send the actual set value back. """
        
        logging.debug(f'{self} sets exposure time.')
        self.camera.exp_time = val

        self.get_exposure_time()


class CameraInterface(Interface):
    def __init__(self, image_label, exp_time_input, res_queue: Queue):
        """Constructor. """

        super().__init__(CAMERA_ID, res_queue)

        # Initialize GUI elements for controling the camera
        self.exp_time_input = exp_time_input

        # Initialize the GUI element for displaying the camera image
        self.image_label = image_label

    def init_subprocess(self):
        """Overwrite the parent function for initializing the subprocess. """

        return CameraSubprocess(self.uid, self.com_queue, self.res_queue)

    def handle_data(self, data):
        """Handle data sent back from the camera subprocess. """

        cmd = data[0]

        if cmd == CMD_DISPLAY_IMAGE:
            self.display_image(data[1])
        elif cmd == CMD_CAMERA_GET_EXP:
            self.display_exp_time(data[1])

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
        """Display the exposure time"""

        logging.debug(f'{self} received exposure {val * 1e6} us from {self.subprocess}.')
        self.exp_time_input.setText(str(val))

    def get_exp_time(self):
        """Query the exposure time from the subprocess. """

        logging.debug(f'{self} querying exposure time.')
        self.com_queue.put((CMD_CAMERA_GET_EXP, ))

    def set_exp_time(self, val):
        """Set the exposure time of the camera. """

        logging.debug(f'{self} setting exposure time to {val * 1e6} us.')
        self.com_queue.put((CMD_CAMERA_SET_EXP, val))

    def stop_recording(self):
        self.com_queue.put((CMD_CAMERA_MODE_STOP, ))

    def set_continuous_mode(self):
        self.com_queue.put((CMD_CAMERA_CONTINOUS_MODE, ))

    def set_rec_mode(self):
        self.com_queue.put((CMD_CAMERA_REC_MODE, ))