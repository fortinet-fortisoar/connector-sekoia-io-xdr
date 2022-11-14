""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import yaml
import configparser

from os.path import abspath, dirname, join, exists

CONFIG_DIR = join(dirname(dirname(abspath(__file__))), 'configs')

CONFIG_FILES_PROPERTIES = ['/opt/cyops/configs/rabbitmq/rabbitmq_users.conf']
CONFIG_FILES_INI = []
CONFIG_FILES_YAML = [join(CONFIG_DIR, 'config.yml'), join(CONFIG_DIR, 'agent_config.yml'),
                     '/opt/cyops/configs/database/db_config.yml', ]


class Config(object):
    config = {}

    def __init__(self):
        for ini_file in CONFIG_FILES_INI:
            if exists(ini_file):
                self.config.update(self.read_ini_file(ini_file))
        for properties_file in CONFIG_FILES_PROPERTIES:
            if exists(properties_file):
                self.config.update(self.read_properties_file(properties_file))
        for yaml_file in CONFIG_FILES_YAML:
            if exists(yaml_file):
                self.config.update(self.read_yaml_file(yaml_file))

    def read_properties_file(self, properties_file_path):
        config = {}
        separators = ['=', ':', ' ']
        with open(properties_file_path, 'r') as properties_file:
            for line in properties_file:
                strip_line = line.strip()
                if strip_line.startswith('#'):
                    continue
                if '#' in strip_line:
                    strip_line = strip_line.split('#', 1)[0].strip()
                for separator in separators:
                    if separator in strip_line:
                        key_value = strip_line.split(separator, 1)
                        key = key_value[0].strip()
                        value = key_value[1].strip()
                        config[key] = value
                        break
        return config

    def read_yaml_file(self, yaml_file_path):
        config = {}
        with open(yaml_file_path, 'r') as yaml_file:
            config.update(yaml.load(yaml_file, Loader=yaml.FullLoader))
        return config

    def read_ini_file(self, ini_file):
        config = {}
        parser = configparser.ConfigParser()
        parser.read(ini_file)
        for section in parser.sections():
            config[section] = dict(parser.items(section))
        return config

    def get(self, section, option=None, fallback=None):
        if option:
            return self.config.get(section).get(option, fallback)
        return self.config.get(section, fallback)


all_config = Config()
