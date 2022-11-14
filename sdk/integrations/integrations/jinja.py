""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import ast
import base64
import json
import requests
import logging

from django.conf import settings
from connectors.models import Connector, Operation, Configuration
from jinja2 import (
    Environment,
)

from connectors.errors.error_constants import *
from connectors.core.connector import ConnectorError

logger = logging.getLogger('connectors')


# filters
def toDict(string: str):
    if not isinstance(string, str):
        raise TypeError('{0} is {1} not string.'.format(string, type(string)))
    return ast.literal_eval(string)


def toJSON(data):
    return json.dumps(json.dumps(data))


def decode_string(attribute_value):
    try:
        if attribute_value:
            return eval(str(base64.b64decode(attribute_value), "utf-8"))
        return attribute_value
    except Exception as e:
        raise Exception('Invalid base64 string provided: {}'.format(attribute_value))


def resolveVault(connector_name, version=None, *args, **kwargs):
    params = kwargs.get('params')
    operation = kwargs.get('operation')
    config_id = kwargs.get('config_id')
    input_data = {
        "connector": decode_string(connector_name),
        "version": decode_string(version) if version else None,
        "params": decode_string(params) if params else {},
        "operation": decode_string(operation) if operation else 'get_credential',
        "config": decode_string(config_id) if config_id else 'get_default_config'
    }

    from connectors.views import ConnectorExecute
    try:
        response, is_binary = ConnectorExecute.execute_connector_operation(input_data)
        return response.get("data", {}).get('password')
    except Connector.DoesNotExist:
        logger.error('Connnector {0} with version {1} not found'.format(connector_name, version))
        raise Exception({'name': connector_name, 'version': version,
                         'message': 'Could not find connector with the specified id or name',
                         'status': ''})

    except ConnectorError as e:
        message = '{0}  Connector :: {1}V{2}'.format(str(e), connector_name, version)
        logger.error(message)
        raise Exception({'message': message})

    except Exception as exp:
        message = '{0} ERROR :: {1}'.format(cs_integration_5, str(exp))
        logger.exception(message)
        raise Exception(
            {'message': message},
        )


# update jinja environment
def environment(**options):
    logger.info('update jinja environment')
    env = Environment(**options)

    # update global functions
    env.globals.update({
        'resolveVault': resolveVault
    })

    # update global filters
    env.filters[toDict.__name__] = toDict
    env.filters[toJSON.__name__] = toJSON
    env.filters[resolveVault.__name__] = resolveVault

    env.autoescape = False
    return env
