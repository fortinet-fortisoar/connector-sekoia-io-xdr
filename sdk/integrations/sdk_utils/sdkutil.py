""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import configparser
from os.path import join, dirname, abspath, isfile, sys
import json
import ast
import re
import getpass

class ConfigUtil:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = join(dirname(dirname(abspath(__file__))), 'configs', 'config.ini')
        self.config.read(self.config_path)

    def get_connector_path(self, name, version):
        connector_name = name + '_' + version
        if connector_name in self.config.keys():
            connector_data = self.config[connector_name]
            path = connector_data['source_path']
            return path
        return None

    def get_connector_config(self, name, version):
        connector_data = self.config[name + '_' + version]
        config = dict(connector_data)
        config.pop('source_path')
        return config

    def add_connector_config(self, name, version, path, params={}):
        connector_name = name + '_' + version
        if connector_name not in self.config.sections():
            self.config.add_section(connector_name)

        if path and path.split() != '':
            self.config[connector_name]['source_path'] = path

        for key, value in params.items():
            self.config[connector_name][key] = value

        # TODO: validate against the valid parameters in the info.json
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        return "Config added successfully"

    def remove_connector(self, name, version):
        return self.config.remove_section(name+ '_' + version)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)
        return "Connector info removed successfully"

config_util = ConfigUtil()


def expand_string(string):
    ret = string
    try:
        ret = json.loads(ret, strict=False)
        return ret
    except Exception:
        pass
    try:
        ret = ast.literal_eval(ret)
        return ret
    except (SyntaxError, ValueError):
        pass
    return ret


def get_input(msg, possible_values=[], val_type='text'):
    while True:
        try:
            if val_type == 'password':
                val = getpass.getpass(prompt=msg)
            else:
                val = input(msg)
            if 'Enter' in msg and not val:
                break
            if (not val) or (str(val).split() == '') or \
                    (len(possible_values) > 0 and val not in possible_values):
                print('\nInvalid input!')
                continue
            else:
                break
        except KeyboardInterrupt:
            print("\nTerminated the process of configuring the custom connector.")
            sys.exit(1)
    return expand_string(val)


def get_input_with_validation(msg, regex, error_msg):
    while True:
        val = input(msg)
        if not re.compile(regex).match(val):
            print('\n' + error_msg)
            continue
        else:
            break
    return expand_string(val)


def get_file_input(msg):
    while True:
        val = input(msg)
        if val and not isfile(str(val)):
            print('\nThe specified file does not exist on the system. Please provide a valid path')
            continue
        else:
            break
    return val


def get_boolean(val):
    if val.lower() == 'y' or val.lower() == 'yes':
        return True
    return False
