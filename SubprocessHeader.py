import logging

# IDs
CAMERA_ID = 0xF1

# Commands
CMD_STOP_SUBPROCESS = 0x00
CMD_DISPLAY_IMAGE = 0x10
CMD_CAMERA_GET_EXP = 0x11
CMD_CAMERA_SET_EXP = 0x12
CMD_RETURN_REC = 0x13
CMD_CAMERA_GET_ROI = 0x14
CMD_CAMERA_SET_ROI = 0x15

CMD_CAMERA_MODE_STOP = 0xA1
CMD_CAMERA_CONTINOUS_MODE = 0xA2
CMD_CAMERA_REC_MODE = 0xA3