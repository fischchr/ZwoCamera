from Subprocess import *
from SubprocessHeader import *
from ZwoMini import *

from PyQt5.QtGui import QImage, QPixmap
from PIL import Image


class CameraSubprocess(Subprocess):
    def __init__(self, com_queue: Queue, out_queue: Queue):
        super(CameraSubprocess, self).__init__(CAMERA_ID, com_queue, out_queue)
        

    def inloop(self):
        img_data = self.camera.capture_video_frame()
        self.send((CMD_DISPLAY_IMAGE, img_data))

    def handle_input(self, res):
        print(res)
        if res[0] == CMD_CAMERA_GET_EXP:
            exp_time = self.camera.get_exposure_time()
            data = [CMD_CAMERA_GET_EXP, exp_time]
            self.send(data)
        elif res[0] == CMD_CAMERA_SET_EXP:
            exp_time = res[1]
            print(exp_time)
            self.camera.set_exposure_time(exp_time)


    def run(self):

        self.camera = ZwoMini()
        self.camera.set_roi(0, 0, 1280, 960, image_type=ASI_IMG_RAW8)
        #self.camera.set_roi(692, 480, 16, 16, image_type=ASI_IMG_RAW8)
        self.camera.set_exposure_time(1e-3)
        self.camera.set_control_value(ASI_HIGH_SPEED_MODE, 1)

        self.camera.start_video_capture()
        super(CameraSubprocess, self).run()
        self.camera.stop_video_capture()


class CameraInterface(Interface):
    def __init__(self, image_label, exp_time_input, com_queue, res_queue):
        super(CameraInterface, self).__init__(CAMERA_ID, com_queue, res_queue)

        self.image_label = image_label
        self.exp_time_input = exp_time_input


    def handle_data(self, data):
        cmd = data[0]

        if cmd == CMD_DISPLAY_IMAGE:
            self.display_image(data[1])
        elif cmd == CMD_CAMERA_GET_EXP:
            self.display_exp_time(data[1])

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
        self.image_label.setPixmap(qpixmap)

    def display_exp_time(self, val):
        self.exp_time_input.setText(str(val))

    def get_exp_time(self):
        self.command_queue.put((CMD_CAMERA_GET_EXP, ))

    def set_exp_time(self, val):
        self.command_queue.put((CMD_CAMERA_SET_EXP, val))