from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("connector_name")


def list_alerts(config, params):
    url: str = OPERATION_CENTER_BASE_URL
    payload: dict = {
        "status_uuid": params.get("status_uuid"),
        "status_name": params.get("status_name"),
        "short_id": params.get("short_id"),
        "rule_uuid": params.get("rule_uuid"),
        "rule_name": params.get("rule_name"),
        "created_at": params.get("created_at"),
    }

    try:
        response: dict = GenericAPIAction(config, "get", url, params=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
