#!/usr/bin/python3

'''
To make the importing of configuration variables cleaner than adding them to globals() directly
'''

import json

class Config:
    '''Provides the variables from a given JSON file as attributes, for cleaner namespace'''
    def __init__(self, conf_file):
        # get config variables from conf_file into local namespace
        with open(conf_file) as f:
            self.__dict__.update(json.load(f))
