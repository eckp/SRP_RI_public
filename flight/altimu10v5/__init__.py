# -*- coding: utf-8 -*-

'''altimu10v5: Main module

Copyright 2017, Svetoslav Kuzmanov
Licensed under MIT.

Derived from https://github.com/SvetoslavKuzmanov/altimu10v5/blob/master/altimu10v5/__init__.py under the MIT license
Adapted by eckp, referencing similar libraries like https://github.com/tkurbad/mipSIE/tree/master/python/AltIMU-10v5
'''

from .lsm6ds33 import LSM6DS33
from .lis3mdl import LIS3MDL
from .lps25h import LPS25H


class IMU(object):
    '''Set up and control Pololu's AltIMU-10v5.'''

    def __init__(self):
        super(IMU, self).__init__()
        self.lsm6ds33 = LSM6DS33()
        self.lis3mdl = LIS3MDL()
        self.lps25h = LPS25H()
        self.enabled = False
        self.calibrated = False

    def __del__(self):
        del(self.lsm6ds33)
        del(self.lis3mdl)
        del(self.lps25h)

    def enable(self):
        '''Enable all devices.'''
        self.lsm6ds33.enable()
        self.lps25h.enable()
        self.lis3mdl.enable()
        self.enabled = True

    def calibrate(self):
        '''Calibrate the devices that require calibration.'''
        self.lsm6ds33.calibrate()
        self.lps25h.calibrate()
        self.calibrated = True
