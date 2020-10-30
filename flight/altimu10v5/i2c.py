# -*- coding: utf-8 -*-

'''Python I2C library module.

This class has helper methods for I2C SMBus access on a Raspberry PI.
Derived from https://github.com/SvetoslavKuzmanov/altimu10v5/blob/master/altimu10v5/i2c.py under the MIT license
Adapted by eckp
'''

from smbus import SMBus


class I2C(object):
    '''Class to set up and access I2C devices.'''

    def __init__(self, bus_id=1):
        '''Initialize the I2C bus.'''
        self._i2c = SMBus(bus_id)

    def __del__(self):
        '''Clean up.'''
        try:
            del(self._i2c)
        except:
            pass

    def write_register(self, address, register, value):
        '''Write a single byte to a I2C register. 
        Return the value the register had before the write.
        '''
        value_old = self.read_register(address, register)
        self._i2c.write_byte_data(address, register, value)
        return value_old

    def read_register(self, address, register):
        '''Read a single I2C register.'''
        return self._i2c.read_byte_data(address, register)

    def combine_bytes(self, *bytes):
        '''Combine (optional extra low,) low and high bytes to an unsigned 16 or 24 bit value. 
        Requires the bytes to be input from low to high.
        '''
        ret = 0
        for i, byte in enumerate(bytes):
            ret |= byte<<8*i
        return ret

    def combine_signed(self, *bytes):
        '''Combine (optional extra low,) low, and high bytes to a signed 16 or 24 bit value. 
        Requires the bytes to be input from low to high.
        '''
        combined = self.combine_bytes(*bytes)
        return combined if combined < 2**(8*len(bytes)-1) else (combined - 2**(8*len(bytes)))
        
    def read_1d(self, address, registers):
        '''Return a vector with the combined raw signed 16 or 24 bit values
        of the output registers of a 1d sensor, depending on the number of registers.
        '''
        bytes = [self.read_register(address, reg) for reg in registers]
        return self.combine_signed(*bytes)
    
    def read_3d(self, address, registers):
        '''Return a vector with the combined raw signed 16 or 24 bit values
        of the output registers of a 3d sensor, depending on the number of registers per axis.
        The input parameter 'registers' should be a list of lists, following this scheme:
        registers = [[(x_reg_xlo), x_reg_lo, x_reg_hi], [(y_reg_xlo), y_reg_lo, y_reg_hi], [z_...]]
        where the extra low register is optional.
        '''
        n_regs = len(registers)//3
        x_val = self.read_1d(address, registers[0:n_regs])
        y_val = self.read_1d(address, registers[n_regs:2*n_regs])
        z_val = self.read_1d(address, registers[2*n_regs:3*n_regs])
        return [x_val, y_val, z_val]
