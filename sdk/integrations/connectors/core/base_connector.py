""" Copyright start
  Copyright (C) 2008 - 2020 Fortinet Inc.
  All rights reserved.
  FORTINET CONFIDENTIAL & FORTINET PROPRIETARY SOURCE CODE
  Copyright end """
import abc
import logging
from django.conf import settings
from connectors.core.result import Result
from connectors.core.constants import STATE_NOT_CONFIGURED, STATE_DEACTIVATED, STATE_DISCONNECTED, STATE_AVAILABLE
from audit import audit

logger = logging.getLogger("connectors")


class ConnectorError(Exception):
    pass

class CustomConnectorException(Exception):
    pass


class Connector(metaclass=abc.ABCMeta):
    def __init__(self, *args, **kwargs):
        self._result = Result()
        self._info_json = kwargs.get('info_json', {})
        return

    def init(self):
        """
        Optional function that can be implemented by the Connector.
        """
        return True

    def on_app_start(self, config, active):
        """
        Invoked when application starts.
        Optional function that can be overridden on start of application.
        """
        pass

    def on_add_config(self, config, active):
        """
        Invoked when a new configuration is added for the connector.
        Optional function that can be overridden for setting up of a new config.
        """
        pass

    def on_delete_config(self, config):
        """
        Invoked when a configuration is deleted for the connector.
        Optional function that can be overridden for any config teardown function.
        """
        pass

    def on_update_config(self, old_config, new_config, active):
        """
        Invoked when a configuration is updated for the connector.
        Optional function that can be overridden for any config edit function.
        """
        pass

    def on_activate(self, config):
        """
        Invoked when a connector is activated.
        Optional function
        """
        pass

    def on_deactivate(self, config):
        """
        Invoked when a connector is deactivated.
        Optional function
        """
        pass

    def teardown(self, config):
        """
        Invoked when a connector is deleted.
        Optional function that can be overridden for dismantling a connector.
        """
        pass

    @abc.abstractmethod
    def execute(self, config, operation, params, **kwargs):
        """
        Mandatory function for every Connector.
        """
        pass

    def verify_health(self, config, active=False):
        if not active:
            return {
                'message': 'Connector is available but not active. Please activate the connector to check the health.',
                'status': STATE_DEACTIVATED}
        try:
            self.check_health(config)
            return {'message': 'Connector is available', 'status': STATE_AVAILABLE}
        except Exception as exp:
            return {'message': str(exp), 'status': STATE_DISCONNECTED}

    def check_health(self, config=None):
        """
        health check function for every Connector.
        """
        pass

    def clean_up(self):
        """
        Optional function to be implemented by the Connector.
        """
        pass

    def handle_exception(self, exception):
        """
        Optional function that can be implemented by the Connector.
        Called if the Connector::_handle_operation function code throws an
        exception that is not handled.
        """
        self._result.set_result(False, exception=exception)

    def _handle_operation(self, input, **kwargs):
        """
        This function will be called by the connector step for handling of
        the provided operation and params
        """
        status='Success'
        self._result.set_env(kwargs.get('env', {}))
        retval = self.execute(input.get("config", {}), input.get("operation"), input.get("params"), **kwargs)
        if type(retval) is tuple:
            result = retval[0]
            is_binary = retval[1]
        elif isinstance(retval, Result):
            [self._result.__dict__.update({key: value}) for key, value in retval.__dict__.items() if value]
            return self._result.get_result(), self._result.get_binary()
        else:
            result = retval
            is_binary = False
        self._result.set_data(result, is_binary)
        self.clean_up()
        if input.get('audit') is True and not settings.LW_AGENT:
            audit.audit_connector_action(input.get('rbac_info'), status)
        return self._result.get_result(), self._result.get_binary()

    def _get_op_from_annotation(self, annotation):
        for op in self._info_json.get('operations'):
            if op.get('annotation') == annotation:
                return op.get('operation')
