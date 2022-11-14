from connectors.core.connector import get_logger, ConnectorError
from .utils import invoke_rest_endpoint
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def sample_delete(config, params, *args, **kwargs):
    endpoint = params.get('url')
    data = params.get('data')
    if not endpoint:
        raise ConnectorError('Missing required input')

    # next call the rest endpoint on the target server with the required inputs
    # sample code below. to be replaced for the integration
    request_body = {'data': data}

    api_response = invoke_rest_endpoint(config, endpoint, 'DELETE', request_body)
    # data transformation here to add/remove/modify some part of the api response
    # sample code below to add a custom key
    api_response.update({'my_custom_response_key': 'my_custom_value'})
    return api_response
