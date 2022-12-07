""" Copyright start
  Copyright (C) 2008 - 2022 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from sdk_utils.sdkutil import config_util, get_input, expand_string
from sdk_utils import messages
import os
from tabulate import tabulate
from os.path import join, abspath, dirname
from os import pardir, remove
import json
import tarfile
import requests
from integrations.settings import SDK_PORT



def create_tar(path, name):
    tarlocation = abspath(join(__file__, pardir, 'temp', name + '.tgz'))
    print("Creating tar at %s" % tarlocation)
    with tarfile.open(tarlocation, "w:gz") as tar:
        tar.add(path, arcname=name)
    return tarlocation


def get_url(prefix='', params={}, method=None):
        server_url = "http://localhost:" + SDK_PORT + "/integration" + prefix
        if (not method) or (method.upper() != 'POST'):
            server_url += '/?format=json'
        for key, value in params.items():
            server_url = server_url + "&" + key + "=" + value
        return server_url


def get_connector_detail(name, version):
    url = get_url('/connectors/' + name + '/' + version)
    r = requests.post(url)
    if r.ok:
        connector = json.loads(r.content.decode('utf-8'))
        return True, connector
    else:
        return False, None


def register(name, path=None, bundle=None):
    if not path and not bundle:
        return "Missing argument: Provide one of the two inputs - bundle, path."
    remove_bundle = False
    if path:
        # tar the sources
        path = path.rstrip('/')
        path = path.rstrip('\\')
        bundle = create_tar(path, name)
        remove_bundle = True
    # create request with file
    url = get_url('/import-connector/' + name + '/', method='POST')
    with open(bundle, 'rb') as payload:
        import_response = requests.post(url, data=payload)
    if remove_bundle:
        remove(bundle)
    if import_response.ok:
        return "Successfully imported connector"
    else:
        return import_response.content


def export_connector(name, version):
    connector_dir = join(dirname(dirname(abspath(__file__))), 'connectors', '%s_%s' % (name, version.replace('.', '_')))
    tarlocation = create_tar(connector_dir, name)
    return "exported connector to %s" % tarlocation


def check_health(name, version, config):
    url = get_url('/connectors/healthcheck/' + name + '/' + version, {'config': config})
    check_response = requests.get(url)
    return check_response.content


def get_config_inputs(config_fields, config_data):
    for field in config_fields:
        field_name = field['name']
        default_value = field.get('value')
        bool_value = None
        value = None
        options = ''
        if field['editable'] and field['visible']:
            field_msg = field.get('title') + ':'
            if field.get('type', '') == 'select':
                options = ' [' + ' / '.join(field.get('options', [])) + ']'
            if field.get('type', '') == 'checkbox':
                options = ' [True/False]'
            field_msg = field_msg + options
            if default_value:
                field_msg = field_msg + '(Press Enter to use default value "{0}")'.format(
                    (default_value[:75] + '..') if len(default_value) > 75 else default_value)
            field_msg = field_msg + ': '
            if field['required']:
                value = get_input(field_msg, val_type=field['type'])
            else:
                value = input(field_msg)
        if not value:
            value = default_value
        if field['required'] and not value and not default_value:
            return "%s is a required, non-editable field, but no value is provided" % field['title']
        if field['type'] == 'boolean' or field['type'] == 'checkbox':
            value = value.lower()
            if value in ['t', 'true']:
                bool_value = True
            elif value in ['f', 'false']:
                bool_value = False
            else:
                return "Invalid input for '%s'. Provide a valid boolean input (t/true/f/false)." % field['title']
        config_data[field_name] = bool_value if isinstance(bool_value, bool) else value
        if field.get('onchange'):
            onchange_fields = field.get('onchange').get(value)
            if onchange_fields:
                get_config_inputs(onchange_fields, config_data)

def configure(name, version, default=False):
    connector_registered, connector = get_connector_detail(name, version)
    if connector_registered:
        connector_id = connector['id']
        config_fields = (connector['config_schema'])['fields']
        config_name = get_input('Name for the configuration: ')
        config_data = {}
        get_config_inputs(config_fields, config_data)
        configuration = {}
        configuration['connector'] = connector['id']
        configuration['name'] = config_name
        configuration['default'] = default
        configuration['config'] = config_data
        configuration['standalone'] = True
        url = get_url('/configuration')
        update_response = requests.request('post', url, json=configuration, verify=False)
        #update_response = requests.post(url, data=configuration, headers={'Content-Type': 'application/json'})
        if update_response.ok:
            # run health_check
            health_check_response = check_health(name, version, config_name).decode('utf-8')
            print(health_check_response)
            return messages.CONFIGURE_COMPLETE.format(name, version, config_name)
        else:
            print(update_response.content)
            return messages.CONFIGURE_FAILED.format(config_name)


def remove_connector(name, version):
    url = get_url('/connectors/' + name + '/' + version)
    check_response = requests.delete(url)
    if check_response.ok:
        # also remove from config file
        config_util.remove_connector(name, version)
        return "Successfully removed connector"
    else:
        return check_response.content


def get_params(params, op_input):
    for field in params:
        param_name = field['name']
        value = None
        options = ''
        default_value = field.get('value', None)
        if field['editable'] and field['visible']:
            field_msg = field.get('title')
            if field.get('type', '') == 'select':
                options = ' [' + ' / '.join(field.get('options', [])) + ']'
            if field.get('type', '') == 'checkbox':
                options = ' [True/False]'
            field_msg = field_msg + options
            if default_value:
                field_msg = field_msg + '(Press Enter to use default value "{0}")'.format(
                    (default_value[:75] + '..') if len(default_value) > 75 else default_value)
            field_msg = field_msg + ': '
            if field['required']:
                value = get_input(field_msg)
            else:
                value = expand_string(input(field_msg))
        if not value:
            value = field.get('value', None)
        if field['required'] and not value:
            return "%s is a required, non-editable field, but no value is provided" % field['title']
        op_input[param_name] = value
        if field.get('onchange'):
            if isinstance(value, bool):
                value = str(value).lower()
            get_params(field.get('onchange', {}).get(value, []), op_input)


def execute(name, version, config, operation):
    # get operation parameters
    connector_registered, connector = get_connector_detail(name, version)
    if connector_registered:
        operations = connector['operations']
        for op in operations:
            if op['operation'] == operation:
                # the operation matches
                op_input = {}
                params = op['parameters']
                get_params(params, op_input)
                execute_payload = {
                    'operation': operation,
                    'params': op_input,
                    'connector': name,
                    'version': version,
                    'config': config
                }
                execute_url = get_url("/execute/", method='POST')
                execute_response = requests.post(execute_url,
                                                 data=json.dumps(execute_payload),
                                                 headers={'Content-Type': 'application/json'}, timeout=30)
                return execute_response.content
        # TODO: list supported operations here
        return "Unsupported operation."
    return "Unsupported operation."


def list_op(name, version):
    # get the connector details
    connector_registered, connector = get_connector_detail(name, version)
    if connector_registered:
        operations = connector.get('operations',[])
        message = "The following operations are supported on the connector %s:\n" % name
        for operation in operations:
            message = message + operation["operation"] + "\n"
        return message
    else:
        return "Failed to get connector data"


def list_configs(name, version):
    # get the connector details
    connector_registered, connector = get_connector_detail(name, version)
    data = []
    if connector_registered:
        configs = connector['configuration']
        message = "The following configurations have been added for the connector %s:\n" % name
        message = message + 'id' + "\t\t" + 'default' + "\t\t" + 'name' + "\n"
        data.append(["id", "name", "default"])
        for config in configs:
            default = "True" if config['default'] else "False"
            data.append([str(config['id']), config['name'], default])
        return tabulate(data, headers="firstrow")
    else:
        return "Failed to get connector data"


def list_connectors():
    url = get_url('/connectors')
    r = requests.get(url)
    if r.ok:
        connector_data = json.loads(r.content.decode('utf-8'))['data']
        message = "The following connectors are registered:\n"
        data = []
        data.append(["id", "name", "version", "status"])
        for connector in connector_data:
            data.append([str(connector['id']), connector['name'], connector['version'], connector['status']])
        return tabulate(data, headers="firstrow")
    else:
        return "Failed to get connectors data."


def service_operation(action, *args, **kwargs):
    if action == "stop":
        os.system("systemctl stop cyops-integrations-agent postgresql-12")
        message = "service stopped successfully"
    elif action == "start":
        os.system("systemctl start postgresql-12 cyops-integrations-agent")
        message = "service started successfully"
    elif action == "restart":
        os.system("systemctl restart postgresql-12 cyops-integrations-agent")
        message = "service restarted successfully"
    else:
        message= "Invalid operation, please check help for usage"
    return message