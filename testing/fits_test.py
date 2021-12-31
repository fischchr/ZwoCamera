import numpy as np
from astropy.io import fits
from datetime import datetime

data = np.random.rand(10, 64, 64)
data = data.tolist()

hdr = fits.Header()
primary_hdu = fits.PrimaryHDU(data[0], header=hdr)
image_hdus = [primary_hdu] + [fits.ImageHDU(image) for image in data[1:]]
hdul = fits.HDUList(image_hdus)

# YYYY-MM-DD_HH:MM:SS
file_name = f"{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.fits"
hdul.writeto(file_name)
