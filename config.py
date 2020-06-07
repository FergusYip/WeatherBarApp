import json
import os


class Config:
    def __init__(self, dir_path, filename):
        self.dir_path = dir_path
        self.filename = filename

    def save(self, config):
        ''' Save the config to a JSON file in the application support folder '''
        filepath = os.path.join(self.dir_path, self.filename)
        with open(filepath, mode='w') as config_file:
            json.dump(config, config_file)

    def read(self):
        ''' Load the config to a JSON file in the application support folder '''
        filepath = os.path.join(self.dir_path, self.filename)
        with open(filepath, mode='r') as config_file:
            config = json.load(config_file)

            return config


def valid_config(config, reference_config):
    ''' Check if a config is valid according to a reference config '''
    for key in reference_config:
        if not isinstance(config.get(key), type(reference_config[key])):
            return False
    return True
