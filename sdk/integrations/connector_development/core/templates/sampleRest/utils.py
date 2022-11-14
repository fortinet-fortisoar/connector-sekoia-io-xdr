import requests
import json
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def invoke_rest_endpoint(config, endpoint, method='GET', data=None, headers=None):
    if headers is None:
        headers = {'accept': 'application/json'}

    # utility function for a sample rest based integration using basic authentication
    # change as required for the specific integration being built

    server_address = config.get('server_address')
    port = config.get('port', '443')
    username = config.get('username')
    password = config.get('password')
    protocol = config.get('protocol', 'https')
    verify_ssl = config.get('verify_ssl', True)
    if not server_address or not username or not password:
        raise ConnectorError('Missing required parameters')
    url = '{protocol}://{server_address}:{port}{endpoint}'.format(protocol=protocol.lower(),
                                                                  server_address=server_address,
                                                                  port=port,
                                                                  endpoint=endpoint)
    try:
        response = requests.request(method, url, auth=(username, password), verify=verify_ssl,
                                    data=json.dumps(data), headers=headers)
    except Exception as e:
        logger.exception('Error invoking endpoint: {0}'.format(endpoint))
        raise ConnectorError('Error: {0}'.format(str(e)))
    if response.ok:
        return response.json()
    else:
        logger.error(response.content)
        raise ConnectorError(response.content)
