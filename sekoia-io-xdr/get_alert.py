from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


def get_alert(config, params: dict):
    """
    Retrieve a specific alert
    """
    url = f"{OPERATION_CENTER_BASE_URL}/{params['alert_uuid']}"
    payload = dict(
        stix=params.get("include_stix", False),
        comments=params.get("include_comments", True),
        history=params.get("include_history", True),
        countermeasures=params.get("include_countermeasures", True),
    )

    try:
        response = GenericAPIAction(config, "get", url, params=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
