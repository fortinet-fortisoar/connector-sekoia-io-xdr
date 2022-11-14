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

    server_url = config.get('server_url')
    port = config.get('port', '443')
    username = config.get('username')
    token = config.get('token')
    protocol = config.get('protocol', 'https')
    verify_ssl = config.get('verify_ssl', True)
    if not server_url or not username or not token:
        raise ConnectorError('Missing required parameters')
    url = '{protocol}://{server_url}:{port}{endpoint}'.format(protocol=protocol.lower(), server_url=server_url,
                                                              port=port, endpoint=endpoint)
    try:
        response = requests.request(method, url, auth=(username, token), verify=verify_ssl,
                                    data=json.dumps(data), headers=headers)
    except Exception as e:
        logger.exception('Error invoking endpoint: {0}'.format(endpoint))
        raise ConnectorError('Error: {0}'.format(str(e)))
    if response.ok:
        return response.json()
    else:
        logger.error(response.content)
        raise ConnectorError(response.content)
