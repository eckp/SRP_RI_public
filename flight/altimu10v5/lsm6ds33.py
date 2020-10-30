# -*- coding: utf-8 -*-

'''Python library module for LSM6DS33 accelerometer and gyroscope.

This module for the Raspberry Pi computer helps interface the LSM6DS33
accelerometer and gyro. The library makes it easy to read
the raw accelerometer and gyro data through I²C interface 
#and it also provides methods for getting angular velocity and g forces.

The datasheet for the LSM6DS33 is available at
[https://www.pololu.com/file/download/LSM6DS33.pdf?file_id=0J1087]

Derived from https://github.com/SvetoslavKuzmanov/altimu10v5/blob/master/altimu10v5/lsm6ds33.py under the MIT license
Adapted by eckp, referencing similar libraries like https://github.com/tkurbad/mipSIE/tree/master/python/AltIMU-10v5
'''

import math
from .i2c import I2C
from time import sleep


class LSM6DS33(I2C):
    '''Set up and access LSM6DS33 accelerometer and gyroscope.'''

    ADDR = 0x6b  # Gyroscope / accelerometer I2C device address

    # Register addresses
    #  ([+] = used in the code, [-] = not used or useful, [ ] = TBD)
    FUNC_CFG_ACCESS   = 0x01  # [-] Configuration of embedded
                                  #     functions, e.g. pedometer

    FIFO_CTRL1        = 0x06  # [-] FIFO threshold setting
    FIFO_CTRL2        = 0x07  # [-] FIFO control register
    FIFO_CTRL3        = 0x08  # [-] Gyro/Acceleromter-specific FIFO settings
    FIFO_CTRL4        = 0x09  # [-] FIFO data storage control
    FIFO_CTRL5        = 0x0A  # [-] FIFO ODR/Mode selection

    ORIENT_CFG_G      = 0x0B  # [ ] Gyroscope sign/orientation

    INT1_CTRL         = 0x0D  # [-] INT1 pad control - unavailable for AltIMU
    INT2_CTRL         = 0x0E  # [-] INT2 pad control - unavailable for AltIMU
    WHO_AM_I          = 0x0F  # [-] Returns 0x69 (read only)
    CTRL1_XL          = 0x10  # [+] Acceleration sensor control
    CTRL2_G           = 0x11  # [+] Angular rate sensor (gyroscope) control
    CTRL3_C           = 0x12  # [+] Device/communication settings
    CTRL4_C           = 0x13  # [ ] Bandwith/sensor/communication settings
    CTRL5_C           = 0x14  # [ ] Rounding/self-test control
    CTRL6_C           = 0x15  # [ ] Acceleration performance/power mode settings
    CTRL7_G           = 0x16  # [ ] Gyroscope performance/power mode settings
    CTRL8_XL          = 0x17  # [ ] Acceleration sensor settings
    CTRL9_XL          = 0x18  # [ ] Acceleration sensor axis control
    CTRL10_C          = 0x19  # [ ] Gyroscope axis control / misc. settings

    WAKE_UP_SRC       = 0x1B  # [-] Wake up interrupt source register
    TAP_SRC           = 0x1C  # [-] Tap source register
    D6D_SRC           = 0x1D  # [-] Orientation sensing for Android devices

    STATUS_REG        = 0x1E  # [ ] Status register. Shows if new data
                                  #     is available from one or more of the
                                  #     sensors

    OUT_TEMP_L        = 0x20  # [+] Temperature output, low byte
    OUT_TEMP_H        = 0x21  # [+] Temperature output, high byte
    OUTX_L_G          = 0x22  # [+] Gyroscope X output, low byte
    OUTX_H_G          = 0x23  # [+] Gyroscope X output, high byte
    OUTY_L_G          = 0x24  # [+] Gyroscope Y output, low byte
    OUTY_H_G          = 0x25  # [+] Gyroscope Y output, high byte
    OUTZ_L_G          = 0x26  # [+] Gyroscope Z output, low byte
    OUTZ_H_G          = 0x27  # [+] Gyroscope Z output, high byte
    OUTX_L_XL         = 0x28  # [+] Accelerometer X output, low byte
    OUTX_H_XL         = 0x29  # [+] Accelerometer X output, high byte
    OUTY_L_XL         = 0x2A  # [+] Accelerometer Y output, low byte
    OUTY_H_XL         = 0x2B  # [+] Accelerometer Y output, high byte
    OUTZ_L_XL         = 0x2C  # [+] Accelerometer Z output, low byte
    OUTZ_H_XL         = 0x2D  # [+] Accelerometer Z output, high byte

    FIFO_STATUS1      = 0x3A  # [-] Number of unread words in FIFO
    FIFO_STATUS2      = 0x3B  # [-] FIFO status control register
    FIFO_STATUS3      = 0x3C  # [-] FIFO status control register
    FIFO_STATUS4      = 0x3D  # [-] FIFO status control register
    FIFO_DATA_OUT_L   = 0x3E  # [-] FIFO data output, low byte
    FIFO_DATA_OUT_H   = 0x3F  # [-] FIFO data output, high byte

    TIMESTAMP0_REG    = 0x40  # [-] Time stamp first byte data output
    TIMESTAMP1_REG    = 0x41  # [-] Time stamp second byte data output
    TIMESTAMP2_REG    = 0x42  # [-] Time stamp third byte data output

    STEP_TIMESTAMP_L  = 0x49  # [-] Time stamp of last step (for pedometer)
    STEP_TIMESTAMP_H  = 0x4A  # [-] Time stamp of last step, high byte
    STEP_COUNTER_L    = 0x4B  # [-] Step counter output, low byte
    STEP_COUNTER_H    = 0x4C  # [-] Step counter output, high byte

    FUNC_SRC          = 0x53  # [-] Interrupt source register for
                              #     embedded functions

    TAP_CFG           = 0x58  # [-] Configuration of embedded functions
    TAP_THS_6D        = 0x59  # [-] Orientation and tap threshold
    INT_DUR2          = 0x5A  # [-] Tap recognition settings
    WAKE_UP_THS       = 0x5B  # [-] Wake up threshold settings
    WAKE_UP_DUR       = 0x5C  # [-] Wake up function settings
    FREE_FALL         = 0x5D  # [-] Free fall duration settings
    MD1_CFG           = 0x5E  # [-] Function routing for INT1
    MD2_CFG           = 0x5F  # [-] Function routing for INT2

    # Output registers used by the gyroscope
    gyro_registers = [
        OUTX_L_G,  # low byte of X value
        OUTX_H_G,  # high byte of X value
        OUTY_L_G,  # low byte of Y value
        OUTY_H_G,  # high byte of Y value
        OUTZ_L_G,  # low byte of Z value
        OUTZ_H_G,  # high byte of Z value
    ]

    # Output registers used by the accelerometer
    acc_registers = [
        OUTX_L_XL,  # low byte of X value
        OUTX_H_XL,  # high byte of X value
        OUTY_L_XL,  # low byte of Y value
        OUTY_H_XL,  # high byte of Y value
        OUTZ_L_XL,  # low byte of Z value
        OUTZ_H_XL,  # high byte of Z value
    ]

    # Output registers used by the temperature sensor
    lsm_temp_registers = [
        OUT_TEMP_L,  # low byte of temperature value
        OUT_TEMP_H,  # high byte of temperature value
    ]

    def __init__(self, bus_id=1):
        '''Set up I2C connection and initialize some flags and values.'''
        super(LSM6DS33, self).__init__(bus_id)
        self.gyro_enabled = False
        self.acc_enabled = False
        self.lsm_temp_enabled = False

        self.gyro_calibrated = False
        self.gyro_cal = [0, 0, 0]

        # current control register settings, starting point are these defaults
        self.settings = {self.FIFO_CTRL5: 0b00000000,
                         self.CTRL1_XL: 0b01010100,  # 208 Hz, +-16g
                         self.CTRL2_G: 0b01010100,  # 208 Hz, +-500 dps
                         self.CTRL6_C: 0b00000000,
                         self.CTRL7_G: 0b00000000}

    def __del__(self):
        '''Clean up.'''
        try:
            # Power down accelerometer and gyro
            self.writeRegister(self.ADDR, self.CTRL1_XL, 0x00)
            self.writeRegister(self.ADDR, self.CTRL2_G, 0x00)
            super(LSM6DS33, self).__del__()
        except:
            pass

    def enable(self):
        '''Enable all sensors.'''
        # power down device first
        self.write_register(self.ADDR, self.CTRL1_XL, 0b00000000)

        # power on and set default settings
        self.configure()

        # the default settings enable the accelerometer, gyroscope and temperature sensor
        self.gyro_enabled = True
        self.acc_enabled = True
        self.lsm_temp_enabled = True

    # TODO: This configure function appears unmodified in all types of sensor classes,
    #       wouldn't it be better placed in the parent class (I2C in this case)?
    def configure(self, settings={}):
        '''Set the registers to the new settings.'''
        # update the settings
        self.settings.update(settings)

        # write the updated settings
        for register in self.settings:
            self.write_register(self.ADDR, register, self.settings[register])

    def calibrate(self, samples=2000):
        '''Calibrate the gyro's raw values.'''
        for i in range(samples):
            gyro_raw = self.get_gyroscope_raw()

            self.gyro_cal[0] += gyro_raw[0]
            self.gyro_cal[1] += gyro_raw[1]
            self.gyro_cal[2] += gyro_raw[2]

            sleep(0.004)

        self.gyro_cal[0] /= samples
        self.gyro_cal[1] /= samples
        self.gyro_cal[2] /= samples

        self.gyro_calibrated = True

    def get_gyroscope_raw(self):
        '''Return a 3D vector of raw gyro data.'''
        # Check if gyroscope has been enabled
        if not self.gyro_enabled:
            raise(Exception('Gyroscope is not enabled!'))

        sensor_data = self.read_3d(self.ADDR, self.gyro_registers)

        # Return the vector
        if self.gyro_calibrated:
            calibrated_gyro_data = sensor_data
            calibrated_gyro_data[0] -= self.gyro_cal[0]
            calibrated_gyro_data[1] -= self.gyro_cal[1]
            calibrated_gyro_data[2] -= self.gyro_cal[2]
            return calibrated_gyro_data
        else:
            return sensor_data

    def get_accelerometer_raw(self):
        '''Return a 3D vector of raw accelerometer data.'''
        # Check if accelerometer has been enabled
        if not self.acc_enabled:
            raise(Exception('Accelerometer is not enabled!'))

        return self.read_3d(self.ADDR, self.acc_registers)

    def get_temperature_raw(self):
        '''Return the raw temperature sensor data.'''
        if not self.lsm_temp_enabled:
            raise(Exception('Temperature is not enabled'))

        return self.read_1d(self.ADDR, self.lsm_temp_registers)

        
    def get_all_raw(self):
        '''Return all sensor values in a flat list.'''
        return [self.get_temperature_raw(),
                *self.get_gyroscope_raw(),
                *self.get_accelerometer_raw()]
