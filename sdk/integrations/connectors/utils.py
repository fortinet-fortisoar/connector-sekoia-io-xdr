""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import os
import re
import inspect
import importlib
import zipfile
import sys

import pkg_resources
import requests
import logging
import subprocess
import base64
import shutil, psutil, copy
import uuid
import json
import simplejson

from django.conf import settings
from django.db.models import Q
from connectors.core.base_connector import Connector, ConnectorError, STATE_AVAILABLE
from connectors.core.constants import SEALAB_SECRET_KEY
from connectors.models import Connector as ConnectorModel
from connectors.models import Configuration as ConfigurationModel, Team, Role
from connectors.models import Operation as OperationModel
from connectors.serializers import ConnectorDetailSerializer, ConnectorConfigurationSerializer, \
    ConnectorOperationSerializer
from connectors.environment import _expand
from integrations.crudhub import make_request, make_file_upload_request, maybe_json_or_raise
from postman.models import Agent
from utils.config_parser import all_config
from connectors.errors.error_constants import *
from postman.utils.helper import load_connectors_json

from postman.utils.utility import get_peer_publish_action
from postman.core.publisher import Publisher
from integrations.password_utils import *
from annotation.views import add_connector_in_annotation
from urllib3.exceptions import InsecureRequestWarning
from django.core.serializers.json import DjangoJSONEncoder
from postman.utils.constants import execute_action_ack
from django.core.exceptions import PermissionDenied

logger = logging.getLogger('connectors')


def reload_connector_modules(root_dir, connector_name):
    connector_path = os.path.join(root_dir, connector_name)
    connector_module = '%s.%s' % (root_dir, connector_name)
    if root_dir == 'connector_development':
        for dir in os.listdir(connector_path):
            file_details = os.path.splitext(dir)
            connector_module_file = '%s.%s' % (connector_module, file_details[0])
            if file_details[1] == ".py":
                file_module  = importlib.import_module(connector_module_file)
                file_module = importlib.reload(file_module)


def get_connector(item, version, info_json=None):
    try:
        if settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in version:
            root_dir = 'connector_development'
        else:
            root_dir = 'connectors'
        version = '%s' % (version.replace('.', '_'))
        connector_name = '%s_%s' % (item, version)
        reload_connector_modules(root_dir, connector_name)
        connector_module = '%s.%s' % (root_dir, connector_name)
        connector_module = importlib.import_module('%s.connector' % connector_module)
        connector_module = importlib.reload(connector_module)
        for name, obj in inspect.getmembers(connector_module):
            if inspect.isclass(obj) and issubclass(obj, Connector) and not inspect.isabstract(obj):
                try:
                    connector_instance = obj(info_json=info_json)
                except:
                    connector_instance = obj()
                return {'instance': connector_instance}
    except Exception as e:
        return {'instance': None, 'message': str(e)}


def get_connector_instance(conn_name, conn_version, conn_obj=None):
    info_json = {}
    if conn_obj:
        connector_serializer = ConnectorDetailSerializer(conn_obj)
        info_json = connector_serializer.data
    connector = get_connector(conn_name, conn_version, info_json)
    if connector.get('instance'):
        return connector.get('instance')
    else:
        logger.error(
            'Exception occurred while getting the connector instance ERROR :: {0}'.format(connector.get('message')))
        raise ConnectorError(connector.get('message'))


def invalidate_cache():
    if importlib is not None:
        if hasattr(importlib, "invalidate_caches"):
            importlib.invalidate_caches()


def get_connector_version_or_latest(name, version, status='Completed', agent_id=None):
    if not agent_id: agent_id = settings.SELF_ID
    if status:
        connector_instance = ConnectorModel.objects.filter(name=name, version=version, status='Completed',
                                                           agent_id=agent_id)
    else:
        connector_instance = ConnectorModel.objects.filter(name=name, version=version, agent_id=agent_id)
    if not connector_instance.exists() and (version and settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in version):
        raise ConnectorError("Connector {0}  with version {1} doesn't exists".format(name, version))
    if not connector_instance.exists():
        version_latest = None
        if status:
            connectors = ConnectorModel.objects.filter(name=name, status='Completed', agent_id=agent_id, development=False)
        else:
            connectors = ConnectorModel.objects.filter(name=name, agent_id=agent_id, development=False)
        for each_connector in connectors:
            version_current = each_connector.version
            if not version_latest:
                version_latest = version_current
            else:
                if tuple(map(int, (version_current.split(".")))) > tuple(map(int, (version_latest.split(".")))):
                    version_latest = version_current
        if version_latest:
            version = version_latest
    return version


def get_connector_or_latest(name, version, status='Completed', agent_id=None):
    if not agent_id:
        agent_id = settings.SELF_ID
    if status:
        connector_instance = ConnectorModel.objects.filter(name=name, version=version, status='Completed',
                                                           agent=agent_id)
    else:
        connector_instance = ConnectorModel.objects.filter(name=name, version=version, agent=agent_id)
    if not connector_instance.exists():
        version_latest = None
        connector_instance_latest = {}
        if status:
            connectors = ConnectorModel.objects.filter(name=name, status='Completed', agent=agent_id)
        else:
            connectors = ConnectorModel.objects.filter(name=name, agent=agent_id)
        for each_connector in connectors:
            version_current = each_connector.version
            if not version_latest:
                version_latest = version_current
                connector_instance_latest = each_connector
            else:
                if tuple(map(int, (version_current.split(".")))) > tuple(map(int, (version_latest.split(".")))):
                    version_latest = version_current
                    connector_instance_latest = each_connector
        if version_latest:
            connector_instance = connector_instance_latest
    else:
        connector_instance = connector_instance.first()
    return connector_instance


def get_connector_path(name, version):
    version = '%s' % (version.replace('.', '_'))
    connector_root_dir = settings.CONNECTORS_DIR
    if settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX in version:
        connector_root_dir = settings.CONNECTOR_DEVELOPMENT_DIR
    return os.path.join(connector_root_dir, ('%s_%s' % (name, version)))


def call_connectors_on_app_start_func(conn_id=None):
    try:
        if is_active_primary()[0]:
            from connectors.models import Connector
            filter = {'status': 'Completed', 'agent_id': settings.SELF_ID}
            if conn_id:
                filter.update({'id': conn_id})
            connectors = Connector.objects.filter(**filter)
            for connector in connectors:
                try:
                    logger.info('Calling on_app_start() for connector %s', connector.name)
                    conn_instance = get_connector_instance(connector.name, connector.version)
                    config = get_configuration(conn_id=connector.id, decrypt=True,
                                               config_schema=connector.config_schema, convert_to_dict=True)
                    conn_instance.on_app_start(config, connector.active)
                except Exception as e:
                    logger.exception('Error while calling connector %s on_app_start function: %s', connector.name,
                                     str(e))
    except:
        pass


def encrypt_password(config_schema, config):
    fields_with_type_pwd = [each_field.get('name') for each_field in config_schema.get('fields', []) if
                            each_field.get('type') == 'password']
    for field in fields_with_type_pwd:
        # for update call if password is NULL string it means there is no change in password field
        if config.get(field) and config.get(field) != 'NULL':
            config[field] = manage_password(data=config[field], action='encrypt')


def decrypt_password(config, config_schema):
    fields_with_type_pwd = [each_field.get('name') for each_field in config_schema.get('fields', []) if
                            each_field.get('type') == 'password']
    for field in fields_with_type_pwd:
        if config.get(field):
            config[field] = manage_password(data=config[field], action='decrypt')


def omit_password(result):
    configurations = result.get('configuration', [])
    config_schema = result.get('config_schema', {})
    fields_with_type_pwd = [each_field.get('name') for each_field in config_schema.get('fields', []) if
                            each_field.get('type') == 'password']
    if isinstance(configurations, list):
        for v in configurations:
            config = v.get('config', {})
            for field in fields_with_type_pwd:
                if field in config:
                    config[field] = 'NULL'
    else:
        config = configurations.get('config', {})
        for field in fields_with_type_pwd:
            if field in config:
                config[field] = 'NULL'


def update_pwd_field(new_config, old_config, config_schema):
    fields_with_type_pwd = [each_field.get('name') for each_field in config_schema.get('fields', []) if
                            each_field.get('type') == 'password']

    for field in fields_with_type_pwd:
        # if the password field received from UI is NULL take the saved password in DB
        # else take the received password
        if new_config.get(field) and new_config.get(field) == 'NULL':
            new_config[field] = manage_password(data=old_config[field], action='decrypt')
        elif new_config.get(field):
            new_config[field] = manage_password(data=new_config[field], action='decrypt')


def on_connector_delete(conn_name, conn_version, config):
    if is_active_primary()[0]:
        get_connector_instance(conn_name, conn_version).teardown(config)


def on_active_status_update(conn_name, conn_version, old_status, new_status, config):
    if old_status != new_status and is_active_primary()[0]:
        conn_instance = get_connector_instance(conn_name, conn_version)
        if new_status:
            conn_instance.on_activate(config)
        else:
            conn_instance.on_deactivate(config)


def process_images(data):
    icon_small, icon_large = '', ''
    try:
        if data.get('icon_small_name'):
            with open(os.path.join(
                    get_connector_path(data.get('name'), data.get('version')),
                    'images', data.get('icon_small_name')), 'rb') as image_file:
                icon_small = 'data:image/jpeg;base64,' + (
                    base64.b64encode(image_file.read())).decode()
    except Exception as e:
        logger.warn('Error while saving icon_small jpeg image %s', str(e))
    try:
        if data.get('icon_large_name'):
            with open(os.path.join(
                    get_connector_path(data.get('name'), data.get('version')),
                    'images', data.get('icon_large_name')), 'rb') as image_file:
                icon_large = 'data:image/jpeg;base64,' + (
                    base64.b64encode(image_file.read())).decode()
    except Exception as e:
        logger.warn('Error while saving icon_small jpeg image %s', str(e))

    return icon_small, icon_large


def get_parsed_config(config, config_schema={}):
    '''
    This function will parse if config is in the form of jinja template.
    :param config:
    :return:
    '''
    try:
        field_type_mapping = {each_field.get('name'): each_field.get('type') for each_field in config_schema.get('fields', [])}
        return {key: _expand({}, value, field_type_mapping.get(key)) for key, value in config.items()}
    except Exception as e:
        logger.error('Error while evaluating jinja template for config %s', str(e))
        raise e


def get_previous_version_details(info, replace=True):
    # this will be used to import the previous version config in new version if config schema is same
    try:
        operations_role_mapping = {}
        prev_config = []
        latest_version = get_connector_version_or_latest(info.get('name'),
                                                         info.get('version'))
        if latest_version and ConnectorModel.objects.filter(name=info.get('name'), version=latest_version,
                                                            status='Completed', agent_id=settings.SELF_ID).exists():
            connector_detail = \
                ConnectorModel.objects.filter(name=info.get('name'), version=latest_version,
                                              agent_id=settings.SELF_ID).first()
            connector_serializer = ConnectorDetailSerializer(connector_detail)
            connector_detail = connector_serializer.data
            operations = connector_detail.get('operations')
            if bool(info.get('configuration')):
                configuration = connector_detail.get('configuration')
                prev_config = import_prev_config(info.get('configuration'), connector_detail.get('config_schema'),
                                          configuration, connector_detail.get('id'), replace)
            if operations:
                for operation in operations:
                    operations_role_mapping[operation.get('operation')] = operation.get('roles')
        return prev_config, operations_role_mapping
    except Exception as e:
        logger.error("Error occurred while importing the previous configuration ERROR :: {0}".format(str(e)))
    return {}


def symlink_system_connector(connector_name, connector_version):
    create_symlink = True
    connectors = ConnectorModel.objects.filter(name=connector_name)
    if len(connectors) > 0:
        for each_connector in connectors:
            version_current = each_connector.version
            if tuple(map(int, (version_current.split(".")))) > tuple(map(int, (connector_version.split(".")))):
                create_symlink = False
                break

    if create_symlink:
        symlink_dir = os.path.join(settings.CONNECTORS_DIR, connector_name)
        # remove previous symlink if any
        try:
            os.unlink(symlink_dir)
        except:
            logger.info('No previous symlink for the connector: %s' % symlink_dir)
        # for upgraded system from cyops < 4.10.3, this could be actual dir
        try:
            shutil.rmtree(symlink_dir)
        except:
            logger.info('No previous directory for connector: %s' % symlink_dir)
        # create the new symlink
        os.symlink(get_connector_path(connector_name, connector_version), symlink_dir)


def get_configuration(conn_id=None, config_id=None, decrypt=False, config_schema={}, convert_to_dict=False):
    try:
        config_object = []
        many = False

        if not bool(config_schema and config_schema.get('fields', [])) and config_id:
            return {}
        elif not config_schema:
            return []

        if config_id:
            config_instance = ConfigurationModel.objects.filter(
                Q(connector=conn_id, config_id=config_id) | Q(connector=conn_id, name=config_id)).first()
            if not config_instance:
                config_instance = ConfigurationModel.objects.filter(connector=conn_id, default=True).first()
            if not config_instance:
                message = 'Could not find a configuration matching the id {0} or the default configuration for the connector'
                logger.error(message.format(config_id))
                raise ConnectorError(message.format(config_id))
            if config_instance.status == 0:
                message = "The configuration {0} is only partially setup. Cannot be used till the configuration is complete"
                logger.error(message.format(config_instance.name))
                raise ConnectorError(message.format(config_instance.name))
        else:
            many = True
            config_instance = ConfigurationModel.objects.filter(connector=conn_id)

        if config_instance:
            serializer = ConnectorConfigurationSerializer(config_instance, many=many)
            config_object = serializer.data

        if isinstance(config_object, list):
            dict_config = {}
            for v in config_object:
                config = v.get('config', {})
                if decrypt:
                    decrypt_password(config, config_schema)
                config = get_parsed_config(config, config_schema)
                config['config_id'] = v.get('config_id')
                config['name'] = v.get('name')
                config['status'] = v.get('status', 0)
                if convert_to_dict:
                    dict_config[config['config_id']] = config
            if convert_to_dict:
                config_object = dict_config

        else:
            config = config_object.get('config', {})
            if decrypt:
                decrypt_password(config, config_schema)
            config = get_parsed_config(config, config_schema)
            config['config_id'] = config_object.get('config_id')
            config['name'] = config_object.get('name')
            config['status'] = config_object.get('status', 0)
            config_object = config

        return config_object

    except ConnectorError as e:
        raise ConnectorError(str(e))
    except Exception as e:
        logger.exception(
            "Error occurred while retrieving configuration with config id : {0} ERROR :: {1} ".format(config_id,
                                                                                                      str(e)))
        raise ConnectorError("Error occurred while retrieving configuration with config id : {0} ".format(config_id))


def get_operation(name=None, conn_id=None):
    try:
        operation_instance = OperationModel.objects.get(connector=conn_id, operation=name, enabled=True)
        serializer = ConnectorOperationSerializer(operation_instance)
        return serializer.data
    except Exception as e:
        raise ConnectorError(
            "Error occurred while retrieving the connector operation {0} ERROR :: {1}".format(name, str(e)))


def config_type_check(name, type, schema):
    for param in schema:
        if name == param.get('name', ''):
            if not type == param.get('type', ''):
                return False
            break
    return True


def get_nested_config_schema(new_onchange_value, param_value, param_name, old_schema):
    new_nested_config = new_onchange_value.get(str(param_value),
                                               new_onchange_value.get(str(param_value).lower(), []))
    new_nested_schema = {"fields": new_nested_config}
    old_nested_config = []
    for old_schema_value in old_schema:
        if old_schema_value.get('name', None) == param_name:
            old_onchange_value = old_schema_value.get('onchange', None)
            if old_onchange_value:
                old_nested_config = old_onchange_value.get(str(param_value),
                                                           old_onchange_value.get(str(param_value).lower(), []))
            break
    old_nested_schema = {"fields": old_nested_config}
    return new_nested_schema, old_nested_schema


def import_prev_config(new_schema, old_schema, configuration, conn_id, replace=True):
    new_schema = new_schema.get('fields', {})
    old_schema = old_schema.get('fields', {})
    for config_object in configuration:
        valid_config = {}
        config = config_object.get('config', {})
        config_status = 1
        for param in new_schema:
            param_name = param.get('name', '')
            param_value = config.get(param_name, None)
            same_type = config_type_check(param_name, param.get('type'), old_schema)
            new_onchange_value = param.get('onchange', None)
            if new_onchange_value:
                new_nested_schema, old_nested_schema = get_nested_config_schema(new_onchange_value, param_value,
                                                                                param_name, old_schema)
                valid_nested_config = import_prev_config(new_nested_schema, old_nested_schema, [config_object], conn_id)
                config_status = valid_nested_config[0].get('status')
                valid_config.update(valid_nested_config[0].get('config'))
            if param_value is None:
                if param.get('value', param.get('default', None)):
                    valid_config[param_name] = param.get('value', param.get('default'))
                elif param.get('required'):
                    config_status = 0
            else:
                if same_type:
                    valid_config[param_name] = param_value
                elif param.get('required'):
                    config_status = 0

        config_object['config'].update(valid_config)
        config_object['status'] = config_status
        config_object['connector'] = conn_id
        config_object['team_ids'] = config_object.pop('teams', [])
        if not replace or not config_object.get('config_id', None):
            config_object['config_id'] = str(uuid.uuid4())
    return configuration


def schema_validator(schema, input):
    missing_required_keys = []
    for param in schema:
        if param.get('required', False):
            param_name = param.get('name', '')
            param_value = input.get(param_name, None)
            param_title = param.get('title', param_name)
            if param_value or isinstance(param_value, int):
                if isinstance(param_value, str):
                    if not param_value.strip():
                        missing_required_keys.append(param_title)
            else:
                missing_required_keys.append(param_title)
    return missing_required_keys


def is_operation_param_valid(operation_schema=None, params={}):
    param_schema = operation_schema.get('parameters', None)
    if not params:
        params = {}
    if param_schema:
        if not isinstance(params, dict):
            raise ConnectorError(
                "Invalid Inputs :: Params provided for a action are of invalid format, Expected in dictionary format")

        missing_required_title = schema_validator(param_schema, params)
        if len(missing_required_title):
            raise ConnectorError(
                "Invalid params provided :: Parameters {0} have either blank value or not provided".format(
                    ', '.join(missing_required_title)))
    return params


def validate_config(config, config_schema={}):
    if not config_schema and config:
        error_message = "Invalid configuration :: You are trying to insert configuration for the connector with no connfiguration schema"
        logger.error(error_message)
        raise ConnectorError(error_message)

    missing_required_keys = schema_validator(config_schema.get('fields', []), config)

    if len(missing_required_keys):
        error_message = "Invalid configuration params provided :: Parameters {0} have either blank value or not provided".format(
            ', '.join(missing_required_keys))
        logger.error(error_message)
        raise ConnectorError(error_message)


def is_active_primary():
    get_non_self_primary = None
    if not settings.LW_AGENT: get_non_self_primary = make_request('/api/auth/cluster/?self=false&primary=true', 'GET')
    if not get_non_self_primary:
        return True, ''
    nodes = get_non_self_primary['nodes']
    if len(nodes) > 0:
        return False, nodes[0]['nodeId']
    return True, ''


def import_playbook(name, label, version, image, override_playbook_info=True):
    if not settings.LW_AGENT:
        playbooks_path = os.path.join(
            get_connector_path(name, version),
            'playbooks',
            'playbooks.json'
        )
        if not os.path.exists(playbooks_path):
            logger.warn('No playbooks to import.')
            return []
        try:
            with open(playbooks_path) as json_data:
                playbook_data = json.load(json_data)
                playbook_exported_tags = playbook_data.get('exported_tags', [])
                playbook_data = playbook_data.get('data')
        except:
            logger.info('%s Playbook Import: Error while reading playbook.json.', name)
            return
        # upload image for PB collection
        try:
            if image and not settings.LW_AGENT:
                image_path = os.path.join(get_connector_path(name, version), 'images', image)
                response = make_file_upload_request(image,
                                                    open(image_path, 'rb'),
                                                    image.replace(' ', '').split('.')[-1],
                                                    'images'
                                                    )
                for el in playbook_data:
                    el['image'] = response.get('@id')
        except Exception as e:
            error_message = str(e)
            error_message = get_truncate_message(error_message, 200)
            logger.warn('%s Playbook Import: Error while uploading image for playbook collection %s', name,
                        error_message)

        # Standardise Playbook collection name and description
        if playbook_data and len(playbook_data) == 1 and override_playbook_info:
            playbook_data[0]['name'] = 'Sample - %s - %s' % (label, version)
            playbook_data[0][
                "description"] = 'Sample playbooks for "%s" connector. If you are planning to use any of the sample playbooks in your environment, ensure that you clone those playbooks and move them to a different collection, since the sample playbook collection gets deleted during connector upgrade and delete.' % label

        if len(playbook_exported_tags):
            playbook_tags = []
            for each_tag in playbook_exported_tags:
                playbook_tags.append({'uuid': each_tag})
            try:
                if not settings.LW_AGENT: make_request('/api/3/bulkupsert/tags', 'POST',
                                                       {"__data": playbook_tags, "__replace": False,
                                                        "__unique": ["uuid"]})
            except Exception as e:
                logger.warn('%s Playbook Tags Import: Error while importing playbook tags: %s', name, str(e))

        result = []
        try:
            if not settings.LW_AGENT:
                playbook_collection = make_request('/api/3/', 'POST', playbook_data)
                result = [{'name': item.get('name'),
                           'description': item.get('description'),
                           '@id': item.get('@id'),
                           'image': item.get('image')
                           } for item in playbook_collection.get('persisted', [])
                          ]
        except Exception as e:
            error_message = str(e)
            error_message = get_truncate_message(error_message, 200)
            logger.warn('%s Playbook Import: Error while importing playbooks: %s', name, error_message)
        return result


def check_broadcast_to_cluster():
    rpm_installed = False
    propagated = False
    cluster_command = None
    try:
        for parent in psutil.Process().parents():
            try:
                cmdline = parent.cmdline()
                if '/bin/yum' in cmdline:
                    rpm_installed = True
                    if 'cs-propagated' in cmdline:
                        propagated = True
                    else:
                        cluster_command = cmdline[1:]
                        if not '-y' in cluster_command:
                            cluster_command.insert(2, '-y')
                        cluster_command = ' '.join(cluster_command) + ' "cs-propagated"'
                        break
            except Exception as e:
                logger.exception('Error fetching process details')
    except Exception as e:
        logger.exception('Error fetching process info')
    return rpm_installed, propagated, cluster_command


def get_response_primary(primaryNodeId, requestURI, method='GET', data=None):
    curl_command = 'curl -X {0} -k https://localhost:9595{1}'.format(method, requestURI)
    if data:
        if not isinstance(data, str):
            data = json.dumps(data)
        data = subprocess.check_output(
            ['/opt/cyops-auth/.env/bin/python', '/opt/cyops/configs/scripts/manage_passwords.py',
             '--encrypt', data]).strip().decode()
        data = json.dumps({"payload": data})
        curl_command += ' -H "Accept: application/json" -H "Content-Type: application/json" -H  "FSR-Encoding: fsr" -d \'' + data + '\''
    response = subprocess.check_output(['sudo', '/bin/hamanager', 'add-command', '--nodeId', primaryNodeId,
                                        '--commandId', 'check-health', '--timeout_in_mins', '1', '--command',
                                        curl_command])
    response_json = json.loads(response.decode('utf-8').strip('\n'))
    connector_response_json = json.loads(response_json['result'])
    return connector_response_json


def get_truncate_message(value, chr_limit):
    if not type(value) == str:
        value = str(value)
    if len(value) > chr_limit:
        return value[:chr_limit] + '...'
    return value


def connector_actions_serializer(connector, connector_fields, permissions=[]):
    connector_object = {}
    roles = []
    if permissions:
        connector_object['has_permissions'] = True
        roles_query = connector.roles.all().values('uuid')
        for roles_query_each in roles_query:
            roles.append(roles_query_each.get('uuid'))
        if roles and not list(set(roles) & set(permissions)):
            connector_object['has_permissions'] = False

    for field in connector_fields:
        connector_object[field] = getattr(connector, field, None)
    return connector_object


def insert_connector(info, playbook_collections=[], config={}, isReserved=False, rpm_installed=False,
                     raise_exception=False, rpm_name='', rpm_full_name='', prev_operation_role={}):
    # validate file and delete if invalid.
    connector_update = False
    try:
        conn_instance = ConnectorModel.objects.filter(name=info.get('name', None), version=info.get('version', None),
                                                      agent_id=info.get('agent', settings.SELF_ID)).first()
        if conn_instance:
            connector_update = True
        else:
            conn_instance = None
        icon_small, icon_large = process_images(info)
        connector_fields = [f.name for f in ConnectorModel._meta.get_fields()]
        connector_data = {}
        info_copy = copy.deepcopy(info)
        for field in connector_fields:
            value = info.get(field, None)
            if value or isinstance(value, bool):
                if field == 'configuration':
                    connector_data['config_schema'] = value
                elif field == 'operations':
                    continue
                else:
                    connector_data[field] = value
                info_copy.pop(field, None)
            elif field == 'configuration':
                connector_data['config_schema'] = {}
                connector_data['config_count'] = -1

        connector_data['system'] = isReserved
        connector_data['icon_small'] = icon_small
        connector_data['icon_large'] = icon_large
        connector_data['playbook_collections'] = playbook_collections
        connector_data['metadata'] = info_copy
        connector_data['metadata']['rpm_installed'] = rpm_installed
        connector_data['rpm_full_name'] = rpm_full_name
        connector_data['migrate'] = True
        connector_data['active'] = True
        connector_data['status'] = 'Completed'
        connector_data['install_result'] = {}
        connector_data['tenant'] = None
        connector_data['requirements_installed'] = 'In-Progress'
        agent_query = Agent.objects.filter(agent_id=connector_data.get('agent', settings.SELF_ID))
        if not agent_query.exists():
            agent_query = Agent.objects.filter(agent_id=settings.SELF_ID)
        agent_instance = agent_query.first()
        agent_id = agent_instance.agent_id
        connector_data['agent'] = agent_id
        connector_data['install_result']['message'] = 'Success'
        connector_data['install_result']['output'] = ''
        remote_status = {'status': 'finished', 'message': 'Success', 'output': ''}
        connector_data['remote_status'] = remote_status

        if connector_update and conn_instance:
            serializer = ConnectorDetailSerializer(conn_instance, data=connector_data, partial=True)
        else:
            serializer = ConnectorDetailSerializer(data=connector_data)
        serializer.is_valid(raise_exception=True)
        conn_instance = serializer.save()

        if bool(config):
            if isinstance(config, list):
                config_count = len(config)
                for each_config in config:
                    each_config['connector'] = conn_instance.id
                configuration_serializer = ConnectorConfigurationSerializer(data=config, many=True)
            else:
                config_count = 1
                configuration_serializer = ConnectorConfigurationSerializer(
                    data={
                        'config_id': config.get(''),
                        'name': config.get('name', ''),
                        'default': config.get('default', False),
                        'config': config,
                        'connector': conn_instance.id
                    }
                )
            configuration_serializer.is_valid(raise_exception=True)
            config_instance = configuration_serializer.save()
            serializer.update(conn_instance, {'config_count': conn_instance.config_count + config_count})

        operations = []
        operation_fields = [f.name for f in OperationModel._meta.get_fields()]
        for operation in info_copy.get('operations', []):
            operation_object = {'connector': conn_instance.id}
            if prev_operation_role:
                operation_name = operation.get('operation')
                roles = prev_operation_role.get(operation_name, [])
                operation_object['role_ids'] = roles
            for field in operation_fields:
                value = operation.get(field, None)
                if value or isinstance(value, bool):
                    operation_object[field] = value
                    operation.pop(field, None)
            operation_object['metadata'] = operation
            operations.append(operation_object)

        if connector_update: OperationModel.objects.filter(connector=conn_instance.id).delete()

        if operations:
            operation_serializer = ConnectorOperationSerializer(data=operations, many=True)
            operation_serializer.is_valid(raise_exception=True)
            operation_serializer.save()
            try:
                if agent_id == settings.SELF_ID:
                    add_connector_in_annotation((serializer.data).get('id'), info)
            except Exception as e:
                logger.warn('Error while adding annotation : %s', str(e))

        result = serializer.data
        result['data'] = info
        omit_password(result)
        invalidate_cache()

        if bool(config) and ('reimport_all_connectors' not in sys.argv):
            call_connectors_on_app_start_func(conn_id=conn_instance.id)

        return result

    except ConnectorError as e:
        raise ConnectorError(str(e))

    except Exception as exp:
        # clean up when went wrong.
        if not raise_exception:
            if conn_instance and connector_update:
                install_result = {}
                install_result['message'] = 'Connector Insertion Failed'
                install_result['output'] = get_truncate_message(exp, 2000)
                remote_status = install_result
                remote_status['status'] = 'failed'
                serializer.update(conn_instance, {'status': 'Failed', 'install_result': install_result,
                                                  'remote_status': remote_status})
            elif conn_instance:
                conn_instance.delete()
            # clean up when went wrong.
            try:
                shutil.rmtree(
                    get_connector_path(info.get('name'), info.get('version')))
            except:
                pass
            logger.exception('{0} ERROR :: {1}'.format(cs_integration_3, str(exp)).format(info.get('name')))
            raise ConnectorError('{0} ERROR :: {1}'.format(cs_integration_3, str(exp)).format(info.get('name')))
        else:
            raise ConnectorError(exp)


def broadcast_message(data, action=None, callback_name=None, method=None, agent_obj=None):
    if not agent_obj:
        logger.info('Broadcast message: Agent obj does not exists returning')
        return False
    elif agent_obj.is_local:
        if not settings.MASTER_ID and Agent.objects.filter(name='Master').exists():
            settings.MASTER_ID = Agent.objects.get(name='Master').agent_id
        destination_id = settings.MASTER_ID
    else:
        destination_id = agent_obj.agent_id

    if not destination_id:
        logger.info('Broadcast: No destination id found returning, current MASTER ID: %s', settings.MASTER_ID)
        return False
    # force publish- is to publish some instruction that does not consists to remote even if
    # self agent has not allowed remote operation. Eg: publish instruction about allow remote operation
    # switch.
    __force_publish = True if data and data.get('__force_publish') else False
    if not (agent_obj.allow_remote_operation or __force_publish):
        logger.info('Agent has not allowed remote connector operation.')
        if not agent_obj.is_local: raise PermissionDenied(cs_integration_16)
        return False
    # When remote connector management is enabled at tenant allow broadcast of all data except when an action is
    # executed for self
    if not data.get('request_id') and action in [execute_action_ack]:
        return False
    pub_config = get_peer_publish_action(callback_name, destination_id)

    message_json = {
        "data": data,
        "status": data.get('status', {}),
        "sourceId": settings.SELF_ID,
        "destinationId": destination_id,
        "action": action,
        "method": method
    }

    try:
        message = json.dumps(message_json)
    except Exception as e:
        try:
            message = simplejson.dumps(message_json)
        except Exception as e:
            message = json.dumps(message_json, cls=DjangoJSONEncoder)

    publisher = Publisher(pub_config)
    publisher.publish(message, destination_id)
    logger.info('Broadcast message: Broadcast Successful for destination %s', destination_id)
    # clean up the file downloaded at agent
    file_cleanup(data.get('env', {}))
    return True


def find_or_update_connector_with_rpm_fullname(conn_object):
    rpm_key = conn_object.first().name + '_' + conn_object.first().version
    settings.CONNECTORS_JSON = load_connectors_json()
    rpm_full_name = settings.CONNECTORS_JSON.get(rpm_key, {}).get('rpm_full_name')
    if not rpm_full_name:
        install_result = {'message': 'rpm_full_name provided is invalid or not found at server'}
        remote_status = install_result
        remote_status['status'] = 'failed'
        conn_object.update(install_result=install_result, remote_status=remote_status)
    return rpm_full_name


def download_connector_rpm(rpm_full_name):
    if not os.path.exists(settings.CONN_RPM_TEMP_DIR):
        os.mkdir(settings.CONN_RPM_TEMP_DIR)
    url = 'https://' + settings.PRODUCT_YUM_SERVER + '/connectors/x86_64/' + rpm_full_name
    filepath = os.path.join(settings.CONN_RPM_TEMP_DIR, rpm_full_name)
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return filepath


def is_replace(connector_name, compatible_version=None):
    if not compatible_version:
        return True

    compatible_version = compatible_version.strip()

    if compatible_version == 'ALL':
        return True

    if compatible_version == 'NULL':
        return False

    if not re.compile(r"[0-9]+.[0-9]+.[0-9]+$").match(compatible_version):
        raise Exception('Incorrect Compatible Version Information')

    connectors = ConnectorModel.objects.filter(name=connector_name)
    if (connectors.count()) > 0:
        compatible_version_map = tuple(map(int, (compatible_version.split("."))))
        for connector in connectors:
            version = connector.version
            if tuple(map(int, (version.split(".")))) < compatible_version_map:
                return False
        return True
    raise Exception('Failed to validate against installed connectors')


def file_cleanup(env, *args, **kwargs):
    file_dir = settings.TMP_FILE_ROOT
    for file_path, metadata in env.get('files', {}).items():
        try:
            if os.path.isdir(file_path):
                shutil.rmtree(file_path)
            else:
                os.remove(os.path.join(file_dir, file_path))
        except Exception as e:
            logger.error(str(e))


def zip_folder(self, destination_zip_file_path, source_zip_folder_path):
    zip_obj = zipfile.ZipFile(destination_zip_file_path + '.zip', 'w', zipfile.ZIP_DEFLATED)
    root_len = len(source_zip_folder_path) + 1
    for base, dirs, files in os.walk(source_zip_folder_path):
        for file in files:
            fn = os.path.join(base, file)
            zip_obj.write(fn, fn[root_len:])


def validate_connector_operation_input(data):
    name = data.get("name")
    version = data.get("version")
    rpm_name = data.get("rpm_name")
    rpm_full_name = data.get("rpm_full_name")
    if name and not re.match("^[\w_-]+$", name):
        raise Exception("Invalid connector name")
    if version and not re.match("^[0-9]+.[0-9]+.[0-9]+$", version.replace(settings.CONNECTOR_DEVELOPMENT_VERSION_POSTFIX, '')):
        raise Exception("Invalid connector version")
    if rpm_name and not re.match("^cyops-connector-[\w_-]+-\d.\d.\d$", rpm_name):
        raise Exception("Invalid connector rpm name")
    # sample rpm full name : cyops-connector-verodin-1.0.0-2532.el7.centos.x86_64.rpm from
    # connectors/info/connectors-all.json
    if rpm_full_name and not re.match("^cyops-connector-[\w_-]+-\d.\d.\d-\d+.*$", rpm_full_name):
        raise Exception("Invalid connector rpm full name")


def check_permission(config_data, operation_data, input_data):
    secret_key = input_data.get('secret_key', '')
    input_roles = input_data.get('rbac_info', {}).get('roles', [])
    input_teams = input_data.get('rbac_info', {}).get('teams', [])
    if isinstance(input_roles, str):
        input_roles = json.loads(input_roles)
    if isinstance(input_teams, str):
        input_teams =json.loads(input_teams)
    try:
        roles = operation_data.get("roles", [])
        teams = config_data.get('teams', [])

        #Checking if it is sealab call by SEALAB_SECRET_KEY
        #Allowed if no roles or team assigined to operation or config
        #Raise error when no role or team found in input role or team
        if roles and not secret_key == SEALAB_SECRET_KEY:
            if not list(set(roles) & set(input_roles)):
                raise Exception("Action {0} is not accessible".format(operation_data.get('operation')))
        if teams and not secret_key == SEALAB_SECRET_KEY:
            if not list(set(teams) & set(input_teams)):
                raise Exception("Configuration {0} is not accessible".format(config_data.get('name')))
    except Exception as e:
        raise Exception("Error occurred while checking the permission for action and configuration ERROR:: {0}".format(str(e)))


def get_or_create_team_or_role(record_type, record_data):
    record_ids = []
    if record_type.lower() == 'role':
        record_object = Role
    elif record_type.lower() == 'team':
        record_object = Team
    else:
        return record_ids

    if record_data:
        for data in record_data:
            if isinstance(data, dict):
                uuid = data.get("uuid", data.get("@id"))
            else:
                uuid = data
            if '/api/3/' in uuid:
                uuid = uuid.split('/')[-1]
            record_query_set = record_object.objects.filter(uuid=uuid)
            if not record_query_set.exists():
                data = {"uuid":uuid}
                team_instance = record_object(**data)
                team_instance.save()
            else:
                team_instance = record_query_set.first()
            record_ids.append(team_instance.uuid)
    return record_ids

def get_update_list(list_items=[], add_items=[], remove_items=[]):
    for add_item in add_items:
        if not add_item in list_items:
            list_items.append(add_item)
    for remove_item in remove_items:
        if remove_item in list_items:
            list_items.remove(remove_item)
    return list_items


def get_ha_nodes():
    get_non_self_primary = None
    secondary_nodes_id = []
    if not settings.LW_AGENT: get_non_self_primary = make_request('/api/auth/cluster/?self=false', 'GET')
    if get_non_self_primary:
        for each_non_self_primary in get_non_self_primary.get('nodes', []):
            secondary_nodes_id.append(each_non_self_primary.get('nodeId'))
    return secondary_nodes_id

def sync_ha_nodes_new(sync_data, sync_method):
    das_url = settings.CRUD_HUB_URL + '/api/auth/clustercommand/' 
    payload = {
        'handlerType' : 'file_handler',
        'commandType' : sync_method,
        'nodeIds' : 'OTHER_NODES',
        'payload' : sync_data
    }

    try:
        response = make_request(das_url, 'POST', payload)
    except Exception as e:
        logger.error('Error occurred while HA Sync ERROR :: {0}'.format(str(e)))

def sync_ha_nodes(path, method):
    try:
        command = ['sudo', '/bin/hamanager', 'add-command', '--handler-type', 'file_handler', '--async',
                   '--command-type', method, '--paths', path, '--nodeId', 'OTHER_NODES']

        response = subprocess.Popen(command)
    except subprocess.CalledProcessError as e:
        error_message = 'Error occurred while progating the sync message to OTHER_NODES'
        logger.error('{0} Error :: {1}'.format(error_message, str(e.output)))
    except Exception as e:
        error_message = 'Error occurred while progating the sync message to OTHER_NODES'
        logger.error('{0} Error :: {1}'.format(error_message, str(e)))


def get_rbac_info(request):
    rbac_info = request.data.get('rbac_info', {})
    if not rbac_info:
        try:
            url = settings.CRUD_HUB_URL + '/api/3/actors/current?$relationships=true'
            auth = request.headers.get('forwarded-authorization') if hasattr(request, 'headers') else None
            request_header = {'Authorization': auth}
            response = requests.request('GET', url, headers=request_header, json=None, verify=False, )
            user_info = maybe_json_or_raise(response)
            source = request.headers.get('X-Forwarded-For') or request.headers.get('X-Remote-Addr')
            rbac_info = {
                'user_iri': user_info.get('uuid'),
                'source': source,
                'teams': user_info.get('teams'),
                'roles': user_info.get('roles'),
            }
        except Exception as e:
            logger.warn('Error occurred while retrieving user info ERROR :: {0}'.format(str(e)))
    return rbac_info


def is_connector_installed(connector_name):
    # No need sudoers permission for /bin/rpm as nginx can run the query on rpm.
    cmd = "/bin/rpm -q " + connector_name + " &>/dev/null"
    ret = os.system(cmd)
    if ret != 0:
        return False
    return True


def identify_if_dependencies_installed(conn_name, conn_version, connector_obj):
    try:
        get_connector_instance(conn_name, conn_version, connector_obj)
        return True
    except ImportError:
        return False
    except Exception as e:
        return False
