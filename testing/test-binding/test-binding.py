#! /usr/bin/env python3
from ctypes import *

CharArr64 = c_char * 64
CharArr16 = c_char * 16
IntArr16 = c_int * 16
IntArr8 = c_int * 8


class ASICameraInfo(Structure):
    _fileds_ = [
        ('Name', CharArr64),
        ('CameraID', c_int),
        ('MaxHeight', c_long),
        ('MaxWidth', c_long),
        ('IsColorCam', c_int),
        ('BayerPattern', c_int),
        ('SupportedBins', IntArr16),
        ('SupportedVideoFormat', IntArr8),
        ('PixelSize', c_double),
        ('MechanicalShutter', c_int),
        ('ST4Port', c_int),
        ('IsCoolerCam', c_int),
        ('IsUSB3Host', c_int),
        ('IsUSB3Camera', c_int),
        ('ElecPerADU', c_float),
        ('BitDepth', c_int),
        ('IsTriggerCam', c_int),
        ('Unused', CharArr16)
    ]


lib = cdll.LoadLibrary("libASICamera2.so")  

lib.ASIGetCameraProperty.argtypes = [POINTER(ASICameraInfo), c_int]
lib.ASIGetCameraProperty.restype = c_int
#print(lib.ASIGetID)

def ASIGetNumOfConnectedCameras():
    res = lib.ASIGetNumOfConnectedCameras()
    #print(res)

def GetProperties(camera_index):
    camera_index = c_int(camera_index)
    camera_info = ASICameraInfo()
    #print(ASICameraInfo.Name)
    p_camera_info = pointer(camera_info)
    #print(camera_info)

    err = lib.ASIGetCameraProperty(p_camera_info, camera_index)
    if err:
        print('Error')
    else:
        pass#print(camera_info)
    #print('Done')

ASIGetNumOfConnectedCameras()
GetProperties(0)

