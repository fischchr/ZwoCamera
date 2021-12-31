from SubprocessHeader import * 
from Subprocess import Subprocess, Interface
from multiprocessing import Queue
from astropy.io import fits


class ImageSubprocess(Subprocess):
    def __init__(self, uid: int, com_queue: Queue, res_queue: Queue):
        super().__init__(uid, com_queue, res_queue)

    def handle_input(self, res):
        if res[0] == CMD_RETURN_REC:
            data = res[1]

    def convert_to_fits(self, data):
        primary_hdu = fits.ImageHDU(data[0])
        # TODO: also get the header
        hdul = fits.HDUList([primary_hdu])
        for image in data[1:]:
            image_hdu = fits.ImageHDU(data)
            hdul.append(image_hdu)

        return hdul