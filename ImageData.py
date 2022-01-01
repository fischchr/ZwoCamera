from astropy.io.fits.hdu.image import ImageHDU
import numpy as np
from astropy.io import fits
from datetime import date, datetime


def _format_date(date: datetime) -> str:
    if isinstance(date, (datetime)):
        fmt = '%Y-%m-%d'
        return date.strftime(fmt)
    else:
        return None

def _format_time(time: datetime) -> str:
    if isinstance(time, (datetime)):
        fmt = '%H:%M:%S'
        return time.strftime(fmt)
    else:
        return None

def load_fits(file_name):
    pass



class ImageData:
    def __init__(self, image_data: list = [], exp_time=None, start_time=None, end_time=None, bit_depth=None):
        # Initialize the image data
        if isinstance(image_data, (np.array)):
            image_data = image_data.tolist()
            
        self._image_data = image_data

        # Set the header entries (all entries which are None will not be saved)
        self._header_data = {
            'DATE': _format_date(start_time),
            'BITPIX': bit_depth,
            'exp_time': exp_time,
            'start_time': _format_time(start_time),
            'end_time': _format_time(end_time)
        }

    def add_image_data(self, image_data: list):
        if isinstance(image_data, (np.array)):
            image_data = image_data.tolist()
        self._image_data += image_data

    def write_fits_to_file(self, file_name: str = '', overwrite=True):
        # Generate the file name if none was given
        if file_name == '':
            if self._header_data['DATE'] is None or self._header_data['start_time'] is None:
                # Use the current time if not both DATE and start_time were set
                now = datetime.utcnow()
                file_name = f"{self._format_date(now)}_{self._format_time(now)}.fits"
            else:
                # Otherwise use DATE and start_time of the data
                file_name = f"{self._header_data['DATE']}_{self._header_data['start_time']}.fits"

        # Get the Header Data Unit list
        hdul = self._generate_fits_image_data()

        # Save data to file
        hdul.writeto(file_name, overwrite=overwrite)

    def _generate_fits_header(self):
        # Initialize the header
        hdr = fits.Header()

        if len(self._image_data):
            # Set Fits header data related to the image
            hdr['DATAMIN'] = np.min(self._image_data)
            hdr['DATAMAX'] = np.max(self._image_data)

        # Set all values of self._header_data which are not None 
        for key, value in self._header_data.items():
            if value is not None:
                hdr[key] = value

        return hdr

    def _generate_fits_image_data(self):
        # Make sure that images have been added
        if len(self._image_data) == 0:
            raise ValueError('No image data to save.')

        # Generate the header
        hdr = self._generate_fits_header()

        # Generate the primary image HDU and add the header
        primary_hdu = fits.PrimaryHDU(self._image_data, header=hdr)

        return fits.HDUList(primary_hdu)


if __name__ == '__main__':
    data = 255 * np.random.rand(10, 64, 64)
    data = data.astype(np.int).tolist()

    image_data = ImageData(data)
    image_data.write_fits_to_file('test.fits')

    #fits_image_filename = '2021-12-31_18:33:29.fits'

    hdul = fits.open('test.fits')
    print(hdul.info())