""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
from connectors.core.connector import Connector
from connectors.core.connector import get_logger, ConnectorError

logger = get_logger('connector_name')

supported_operations = {'operation_name': None}


class Temp(Connector):

    def execute(self, config, operation, params, **kwargs):
        operation = supported_operations.get(operation)
        return operation(config, params)

    def check_health(self, config=None):
        pass
