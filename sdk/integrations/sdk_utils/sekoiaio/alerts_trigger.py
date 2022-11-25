from connectors.core.connector import get_logger, ConnectorError

logger = get_logger('connector_name')


def alerts_trigger(config, params):
    # return the value you would want as output of this operation
    # raise ConnectorError for scenarios where the operation should fail
    return {'key1': 'val1'}