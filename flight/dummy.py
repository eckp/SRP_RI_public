#!/usr/bin/python3

'''Dummy class to provide objects that can be used to replace missing interfaces, 
which then log any calls to that object.'''

import random
import ast
import logging

# because this is a module to be imported, make this logger a child of the main file's logger
logger = logging.getLogger('__main__.'+__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

class Input:
    '''Dummy object to replace input peripherals.
It replaces calls to any method of the object by an input statement,
informing about the call and asking for an answer.'''
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        def method(*args, **kwargs):
            ret = input('{} was requested from {} with arguments {} and kwargs {}. Return what? '\
                        .format(name, self.obj, args, kwargs))
            # if the input is meant to be numeric, try evaluating it. If it doesn't work, leave ret a string
            # this is to evaluate only values, nothing else (no variables, functions etc...)
            try:
                ret = ast.literal_eval(ret)  
            except ValueError:
                pass
            logger.info('{} was requested from {} with arguments {} and kwargs {}. Returned value: {}'\
                        .format(name, self.obj, args, kwargs, ret))
            return ret
        return method


class Sensor:
    '''Dummy object to replace sensors.
It returns random values to any method call on the object.
It does not log anything by default, to prevent flooding the logs.
If logging is enabled, it logs to the DEBUG level, to prevent flooding INFO'''
    def __init__(self, obj, log=False, rand_range=(-10,10)):
        self.obj = obj
        self.log = log
        self.rand_range = rand_range

    def __getattr__(self, name):
        def method(*args, **kwargs):
            ret = random.uniform(*rand_range)
            if self.log:
                logger.debug('{} was requested from {} with arguments {} and kwargs {}. Returned value: {}'\
                             .format(name, self.obj, args, kwargs, ret))
            return ret
        return method


class Output:
    '''Dummy object to replace output peripherals.
It replaces calls to any method of the object by a logging statement,
informing about the call and its arguments.'''
    def __init__(self, obj):
        self.obj = obj

    def __getattr__(self, name):
        def method(*args, **kwargs):
            logger.info('{} was called on {} with arguments {} and kwargs {}'\
                        .format(name, self.obj, args, kwargs))
        return method


#class Profiler:
#    '''Dummy object to replace profiler and its function decorators in case we don't need it.'''
#    def __init__(self):
#        pass

#    def profile(self, func):
#        def method(*args, **kwargs):
#            return func(*args, **kwargs)
#        return method
