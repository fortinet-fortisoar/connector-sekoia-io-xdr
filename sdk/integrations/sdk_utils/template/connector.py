from connectors.core.connector import get_logger, Connector
from .health_check import check

logger = get_logger('connector_name')


class Template(Connector):

    def execute(self, config, operation, params, **kwargs):
        supported_operations = {'Operation 1': function_template}
        return supported_operations[operation](config, params)

    def check_health(self, config):
        return check(config)
