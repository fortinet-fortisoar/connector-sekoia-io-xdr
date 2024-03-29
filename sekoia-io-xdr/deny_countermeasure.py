from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")

def deny_countermeasure(config, params):
    """
    Deny a countermeasure
    """
    url: str = f"{OPERATION_CENTER_BASE_URL}/countermeasures/{params['countermeasure_uuid']}/deny"
    data: dict = {
        "comment": {"content": params["content"], "author": params.get("author")}
    }

    try:
        response = GenericAPIAction(config, "PATCH", url, json=data).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
