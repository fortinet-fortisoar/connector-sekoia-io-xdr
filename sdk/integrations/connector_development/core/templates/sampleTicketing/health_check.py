from .utils import invoke_rest_endpoint
from connectors.core.connector import get_logger, ConnectorError
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def health_check(config=None, *args, **kwargs):
    # template code. to be replaced with health check APIs and authentication method for the specific integration
    # sample health check URL
    auth_endpoint = '/api/auth'

    # the utility function raises an exception if the response is not one of the success responses
    invoke_rest_endpoint(config, auth_endpoint, 'POST')

    # will reach here only if the previous api_call was a success
    return 'Connector is Available'
