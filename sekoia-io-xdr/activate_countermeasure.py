from connectors.core.base_connector import ConnectorError

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction
from connectors.core.connector import get_logger


logger = get_logger("sekoia-io-xdr")

def activate_countermeasure(config, params):
    """
    Activate a countermeasure
    """
    url: str = f"{OPERATION_CENTER_BASE_URL}/countermeasures/{params['countermeasure_uuid']}/activate"
    data: dict = {
        "comment": {"content": params["content"], "author": params.get("author")}
    }

    try:
        response = GenericAPIAction(config, "PATCH", url, json=data).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
