
from connectors.core.connector import get_logger, ConnectorError
from .utils import invoke_rest_endpoint
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def add_comment(config, params, *args, **kwargs):
    endpoint = params.get('endpoint')
    ticket_id = params.get('ticket_id')
    ticket_comment = params.get('comment')
    if not ticket_comment or not ticket_id:
        raise ConnectorError('Missing required input')

    endpoint = "{0}{1}".format(endpoint, ticket_id)

    # next call the rest endpoint on the target server with the required inputs
    # sample code below. to be replaced for the integration
    request_body = {
    	'comment': ticket_comment
    }

    api_response = invoke_rest_endpoint(config, endpoint, 'POST', request_body)
    
    # data transformation here to add/remove/modify some part of the api response
    # sample code below to add a custom key
    api_response.update({'my_custom_response_key': 'my_custom_value'})
    return api_response
