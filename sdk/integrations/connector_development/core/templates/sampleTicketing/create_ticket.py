from connectors.core.connector import get_logger, ConnectorError
from .utils import invoke_rest_endpoint
from .constants import LOGGER_NAME

logger = get_logger(LOGGER_NAME)


def create_ticket(config, params, *args, **kwargs):
    ticket_summary = params.get('ticket_summary', '')
    ticket_description = params.get('ticket_description', '')
    ticket_type = params.get('ticket_description', '')
    endpoint = '/api/tickets'

    # next call the rest endpoint on the target server with the required inputs
    # sample code below. to be replaced for the integration
    request_body = {
        'ticket_summary': ticket_summary,
        'ticket_description': ticket_description,
        'ticket_type': ticket_type
    }

    api_response = invoke_rest_endpoint(config, endpoint, 'POST', request_body)

    # data transformation here to add/remove/modify some part of the api response
    # sample code below to add a custom key
    api_response.update({'my_custom_response_key': 'my_custom_value'})
    return api_response
