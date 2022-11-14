#!/usr/bin/env python
""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from sdk_utils import run, build
from argparse import ArgumentParser
from sdk_utils import messages
import sys


class Argument:
    def __init__(self, name, help, type, is_required):
        self.name = name
        self.arg_name = '--' + name
        self.help = help
        self.type = type
        self.is_required = is_required

    def add_to_parser(self, parser):
        parser.add_argument(self.arg_name, help=self.help, required=self.is_required, type=self.type)


class Option:
    def __init__(self, name, function, required_args=(), optional_args=()):
        self.name = name
        self.function = function
        self.required_args = required_args
        self.optional_args = optional_args

    def validate(self, args):
        params = {}
        for required_arg in self.required_args:
            name = required_arg.name
            value = args.get(name, None)
            if not value:
                raise ValueError("Missing required argument: %s" % name)
            params[name] = value
        for optional_arg in self.optional_args:
            name = optional_arg.name
            value = args.get(name, None)
            if value:
                params[name] = value
        return params

    def execute(self, args):
        params = self.validate(args)
        return self.function(**params)


def runserver():
        from manage import main
        main(['', 'runserver'])


def init():
    name = Argument('name', 'name of the connector', str, False)
    version = Argument('version', 'version of the connector', str, False)
    path = Argument('path', 'path to connector folder', str, False)
    bundle = Argument('bundle', 'path to the connector archive', str, False)
    operation = Argument('operation', 'operation to execute on the connector', str, False)
    config_name = Argument('config', 'configuration to be used', str, False)
    action = Argument('action', 'agent services start| stop| restart', str, False)
    default = Argument('default', 'Mark the configuration as default', bool, False)

    op_runserver = Option('runserver', runserver)

    op_create_template = Option('create_template', build.copy_connector_folder, (name, version))
    op_add_info = Option('add_info', build.add_connector_info, (name, version))
    op_add_config_params = Option('add_config_params', build.add_config_params, (name, version))
    op_add_operation = Option('add_operation', build.add_functions, (name, version))

    op_import = Option('import', run.register, (name,), (path, bundle))
    op_export = Option('export', run.export_connector, (name, version),)
    op_configure = Option('configure', run.configure, (name, version,), (default,))
    op_health_check = Option('check_health', run.check_health, (name, version, config_name))
    op_execute = Option('execute', run.execute, (name, version, config_name, operation))
    op_remove = Option('remove', run.remove_connector, (name, version))
    op_list_operations = Option('list_operations', run.list_op, (name, version))
    op_list_configs = Option('list_configs', run.list_configs, (name, version))
    op_list_connectors = Option('list_connectors', run.list_connectors, ())
    op_services = Option('services', run.service_operation, (action,), ())

    all_options = (op_runserver,
                   op_create_template, op_add_info,
                   op_add_config_params, op_add_operation,
                   op_import, op_configure,
                   op_health_check, op_execute,
                   op_remove, op_export,
                   op_list_operations, op_list_configs, op_list_connectors,
                   op_services)

    option_desc = ''
    for opt in all_options:
        option_desc += opt.name + '| '
    option = Argument('option', option_desc, str, True)

    all_args = (option, name, version, path, bundle, operation, config_name, action, default)
    return all_args, all_options


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print(messages.WELCOME.encode('ascii', 'ignore').decode('ascii'))
        sys.exit(1)

    arg_parser = ArgumentParser(description='')
    all_args, all_options = init()
    for arg in all_args:
        arg.add_to_parser(arg_parser)

    args = arg_parser.parse_args()
    option_name = args.option
    #find the option
    for option in all_options:
        if option.name == option_name:
            args_dict = vars(args)
            try:
                cmd_response = option.execute(args_dict)
                print(cmd_response)
            except Exception as e:
                print(str(e))
            sys.exit(0)
    print("\nError: Unsupported function")
    sys.exit(1)

