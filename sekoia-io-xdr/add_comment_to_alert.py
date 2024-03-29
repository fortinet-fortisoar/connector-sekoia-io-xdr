from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


def add_comment_to_alert(config, params: dict):
    """
    Add a comment to an alert
    """
    url = f"{OPERATION_CENTER_BASE_URL}/{params['alert_uuid']}/comments"
    body = dict(content=params["comment"], author=params["author"])

    try:
        response = GenericAPIAction(config, "POST", url, json=body).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
