# -*- coding: utf-8 -*-

'''Python library module for LIS3MDL magnetometer.

This module for the Raspberry Pi computer helps interface the LIS3MDL
magnetometer. The library makes it easy to read the raw magnetometer
through I²C interface.

The datasheet for the LSM6DS33 is available at
[https://www.pololu.com/file/download/LIS3MDL.pdf?file_id=0J1089]

Derived from https://github.com/SvetoslavKuzmanov/altimu10v5/blob/master/altimu10v5/lis3mdl.py under the MIT license
Adapted by eckp, referencing similar libraries like https://github.com/tkurbad/mipSIE/tree/master/python/AltIMU-10v5
'''

from .i2c import I2C


class LIS3MDL(I2C):
    '''Set up and access LIS3MDL magnetometer.'''

    ADDR = 0x1e  # Magnetometer I2C device address

    # Register addresses
    #  ([+] = used in the code, [-] = not used or useful, [ ] = TBD)
    WHO_AM_I    = 0x0F   # [-] Returns 0x3d (read only)

    CTRL_REG1   = 0x20   # [+] Control register to enable device, set
                         #     operating modes and rates for X and Y axes
    CTRL_REG2   = 0x21   # [+] Set gauss scale
    CTRL_REG3   = 0x22   # [+] Set operating/power modes
    CTRL_REG4   = 0x23   # [+] Set operating mode and rate for Z-axis
    CTRL_REG5   = 0x24   # [ ] Set fast read, block data update modes

    STATUS_REG  = 0x27   # [ ] Read device status (Is new data available?)

    OUT_X_L     = 0x28   # [+] X output, low byte
    OUT_X_H     = 0x29   # [+] X output, high byte
    OUT_Y_L     = 0x2A   # [+] Y output, low byte
    OUT_Y_H     = 0x2B   # [+] Y output, high byte
    OUT_Z_L     = 0x2C   # [+] Z output, low byte
    OUT_Z_H     = 0x2D   # [+] Z output, high byte

    TEMP_OUT_L  = 0x2E   # [+] Temperature output, low byte
    TEMP_OUT_H  = 0x2F   # [+] Temperature output, high byte

    INT_CFG     = 0x30   # [-] Interrupt generation config
    INT_SRC     = 0x31   # [-] Interrupt sources config
    INT_THS_L   = 0x32   # [-] Interrupt threshold, low byte
    INT_THS_H   = 0x33   # [-] Interrupt threshold, high byte

    # Output registers used by the magnetometer
    mag_registers = [
        OUT_X_L,    # low byte of X value
        OUT_X_H,    # high byte of X value
        OUT_Y_L,    # low byte of Y value
        OUT_Y_H,    # high byte of Y value
        OUT_Z_L,    # low byte of Z value
        OUT_Z_H,    # high byte of Z value
    ]

    # Output registers used by the temperature sensor
    lis_temp_registers = [
        TEMP_OUT_L, # low byte of temperature value
        TEMP_OUT_H, # high byte of temperature value
    ]


    def __init__(self, bus_id=1):
        '''Set up I2C connection and initialize some flags and values.'''
        super(LIS3MDL, self).__init__(bus_id)
        self.mag_enabled = False
        self.lis_temp_enabled = False

        # current control register settings, starting point are these defaults
        self.settings = {self.CTRL_REG1: 0b11100010,
                         self.CTRL_REG2: 0b00000000,
                         self.CTRL_REG3: 0b00000000,
                         self.CTRL_REG4: 0b00001100}

    def __del__(self):
        '''Clean up.'''
        try:
            # Power down magnetometer
            self.write_register(self.ADDR, self.CTRL_REG3, 0x03)
            super(LIS3MDL, self).__del__()
        except:
            pass

    def enable(self):
        '''Enable and set up the the magnetometer and determine
        whether to auto increment registers during I2C read operations.
        '''
        # Disable magnetometer and temperature sensor first
        self.write_register(self.ADDR, self.CTRL_REG1, 0x00)
        self.write_register(self.ADDR, self.CTRL_REG3, 0x03)

        # power on and set default settings
        self.configure()

        # the default settings enable the magnetometer and the temperature sensors
        self.mag_enabled = True
        self.lis_temp_enabled = True

    def configure(self, settings={}):
        '''Set the registers to the new settings.'''
        # update the settings
        self.settings.update(settings)

        # write the updated settings
        for register in self.settings:
            self.write_register(self.ADDR, register, self.settings[register])
        
    def get_magnetometer_raw(self):
        '''Return 3D vector of raw magnetometer data.'''
        # Check if magnetometer has been enabled
        if not self.mag_enabled:
            raise(Exception('Magnetometer is not enabled'))

        return self.read_3d(self.ADDR, self.mag_registers)

    def get_temperature_raw(self):
        '''Return the raw temperature sensor data.'''
        if not self.lis_temp_enabled:
            raise(Exception('Temperature is not enabled'))

        return self.read_1d(self.ADDR, self.lis_temp_registers)

    def get_all_raw(self):
        '''Return all sensor data as a flat list.'''
        return [self.get_temperature_raw(), *self.get_magnetometer_raw()]
