# -*- coding: utf-8 -*-

'''Python module for LPS25H digital barometer.

This module for the Raspberry Pi computer helps interface the LPS25H
digital barometer. The library makes it easy to read the raw barometer
through I²C interface.

The datasheet for the LPS25H is available at
[https://www.pololu.com/file/download/LPS25H.pdf?file_id=0J761]

Derived from https://github.com/SvetoslavKuzmanov/altimu10v5/blob/master/altimu10v5/lps25h.py under the MIT license
Adapted by eckp, referencing similar libraries like https://github.com/tkurbad/mipSIE/tree/master/python/AltIMU-10v5
'''

from .i2c import I2C
from time import sleep


class LPS25H(I2C):
    '''Set up and access LPS25H digital barometer.'''

    ADDR = 0x5d  # Barometric pressure I2C device address

    # Register addresses
    #  ([+] = used in the code, [-] = not used or useful, [ ] = TBD)
    REF_P_XL        = 0x08  # [ ] Reference pressure, lowest byte
    REF_P_L         = 0x09  # [ ] Reference pressure, low byte
    REF_P_H         = 0x0A  # [ ] Reference pressure, high byte

    WHO_AM_I        = 0x0F  # [-] Returns 0xbd (read only)

    RES_CONF        = 0x10  # [ ] Set pressure and temperature resolution

    CTRL_REG1       = 0x20  # [+] Set device power mode / ODR / BDU
    CTRL_REG2       = 0x21  # [-] FIFO / I2C configuration
    CTRL_REG3       = 0x22  # [-] Interrupt configuration
    CTRL_REG4       = 0x23  # [-] Interrupt configuration

    INT_CFG         = 0x24  # [-] Interrupt configuration
    INT_SOURCE      = 0x25  # [-] Interrupt source configuration

    STATUS_REG      = 0x27  # [ ] Status (new pressure/temperature data
                            #     available)

    PRESS_OUT_XL    = 0x28  # [+] Pressure output, loweste byte
    PRESS_OUT_L     = 0x29  # [+] Pressure output, low byte
    PRESS_OUT_H     = 0x2A  # [+] Pressure output, high byte

    TEMP_OUT_L      = 0x2B  # [+] Temperature output, low byte
    TEMP_OUT_H      = 0x2C  # [+] Temperature output, high byte

    FIFO_CTRL       = 0x2E  # [ ] FIFO control / mode selection
    FIFO_STATUS     = 0x2F  # [-] FIFO status

    THS_P_L         = 0x30  # [-] Pressure interrupt threshold, low byte
    THS_P_H         = 0x31  # [-] Pressure interrupt threshold, high byte

    # The next two registers need special soldering and are not
    # available on the AltIMU
    RPDS_L          = 0x39  # [-] Pressure offset for differential
                            #     pressure computing, low byte
    RPDS_H          = 0x3A  # [-] Differential offset, high byte

    # Registers used for reference pressure
    ref_registers = [
        REF_P_XL, # lowest byte of reference pressure value
        REF_P_L,  # low byte of reference pressure value
        REF_P_H,  # high byte of reference pressure value
    ]

    # Output registers used by the pressure sensor
    baro_registers = [
        PRESS_OUT_XL, # lowest byte of pressure value
        PRESS_OUT_L,  # low byte of pressure value
        PRESS_OUT_H,  # high byte of pressure value
    ]

    # Output registers used by the temperature sensor
    lps_temp_registers = [
        TEMP_OUT_L, # low byte of temperature value
        TEMP_OUT_H, # high byte of temperature value
    ]

    
    def __init__(self, bus_id=1):
        '''Set up and access LPS25H digital barometer.'''
        super(LPS25H, self).__init__(bus_id)
        self.baro_enabled = False
        self.lps_temp_enabled = False

        self.p0 = 101325  # standard sea level pressure in Pa as a first guesstimate

        # current control register settings, starting point are these defaults
        self.settings = {self.CTRL_REG1: 0b10110000,
                         self.CTRL_REG2: 0b00000000,
                         self.CTRL_REG3: 0b00000000,
                         self.CTRL_REG4: 0b00000000}

    def __del__(self):
        '''Clean up.'''
        try:
            # Power down the device
            self.write_register(self.ADDR, self.CTRL_REG1, 0x00)
            super(LPS25H, self).__del__()
        except:
            pass

    def enable(self):
        '''Enable and set up the LPS25H barometer.'''
        # Power down device first
        self.write_register(self.ADDR, self.CTRL_REG1, 0x00)

        # power on and set default settings
        self.configure()

        # the default settings enable the barometer and temperature sensor
        self.baro_enabled = True
        self.lps_temp_enabled = True

    def configure(self, settings={}):
        '''Set the registers to the new settings.'''
        # update the settings
        self.settings.update(settings)

        # write the updated settings
        for register in self.settings:
            self.write_register(self.ADDR, register, self.settings[register])

# TODO: this is not a calibration in the truest sense,
#       as the sensor returns absolute readings w.r.t. a reference reservoir.
#       Instead, this is an initialisation where the reference altitude is established...
    def calibrate(self, samples=2000):
        '''Measure the current ambient pressure 
        by exponentially averaging n_samples pressure readings.'''
        for i in range(samples):
            self.p0 = 0.95*self.p0 + 0.05*(self.get_barometer_raw()/40.96)
            sleep(0.004)

        self.baro_calibrated = True
        return self.p0

            
    def get_barometer_raw(self):
        '''Return the raw barometer sensor data.'''
        # Check if barometer has been enabled
        if not self.baro_enabled:
            raise(Exception('Barometer is not enabled'))

        return self.read_1d(self.ADDR, self.baro_registers)

    def get_temperature_raw(self):
        '''Return the raw temperature sensor data.'''
        if not self.lps_temp_enabled:
            raise(Exception('Temperature is not enabled'))

        return self.read_1d(self.ADDR, self.lps_temp_registers)

    def get_all_raw(self):
        '''Return all sensor data.'''
        return [self.get_temperature_raw(), self.get_barometer_raw()]
