from zwoasi import init, Camera, ASI_EXPOSURE, ASI_IMG_RAW8, ASI_HIGH_SPEED_MODE, list_cameras, ASI_COOLER_ON, ASI_FAN_ON, ASI_TEMPERATURE, ASI_TARGET_TEMP
from matplotlib import pyplot as plt
import numpy as np
import time

init('libASICamera2.so')
c = Camera('ZWO ASI174MM-Cool')
#c = Camera('ZWO ASI120MM Mini')

def set_exposure_time(exp_time):
    exp_time_us = int(exp_time * 1e6)
    c.set_control_value(ASI_EXPOSURE, exp_time_us)


set_exposure_time(500e-6)
c.set_control_value(ASI_HIGH_SPEED_MODE, 1)

if c.get_camera_property()['IsCoolerCam']:
    c.set_control_value(ASI_COOLER_ON, 1)
    c.set_control_value(ASI_FAN_ON, 1)
    c.set_control_value(ASI_TARGET_TEMP, -5)
    #for i in range(10):
    #    time.sleep(5)
    #    print(c.get_control_value(ASI_TEMPERATURE)[0])


# Get an image with full resolution
c.set_roi(0, 0, 1280, 960)
t1 = time.time()
img = c.capture()
print(time.time() - t1)
#plt.imshow(img)

# Get an image with 16x16 pixel resolution 
c.set_roi(692, 480, 16, 16, image_type=ASI_IMG_RAW8)
t1 = time.time()
img = c.capture()
print(time.time() - t1)

# Some video capturing
n_images = 1000
width = 128
height = 128
c.set_roi(0, 0, width, height)

c.start_video_capture()
#img = 16 * [bytearray[16]]
res = []
t1 = time.time()
print(f'{time.time():.32f}')
for i in range(n_images):
    res.append(c.capture_video_frame())
c.stop_video_capture()
t2 = time.time()
print(t2 - t1, n_images / (t2 - t1))

img_array = np.array(res)

# Slightly faster
img = bytearray(width * height * [0])
data = np.zeros((n_images, len(img)))
# Data type: little endian 1 byte
dt = np.dtype('<i1')

c.start_video_capture()
t1 = time.time()
for i in range(n_images):
    c.get_video_data(buffer_=img)
    data[i, :] = np.frombuffer(img, dtype=dt)
    #data.append(list(img))
c.stop_video_capture()
t2 = time.time()
print(t2 - t1, n_images / (t2 - t1))


img = np.reshape(data[0, :], (height, width), order='C')
#print(len(data[0]))

plt.imshow(img)
plt.show()


