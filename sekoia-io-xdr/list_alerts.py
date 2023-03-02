from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


def list_alerts(config, params):
    url: str = OPERATION_CENTER_BASE_URL

    if params.get("start_date") and params.get("end_date"):
        created_at = f"{params['start_date']}, {params['end_date']}"
    else:
        created_at = None

    payload: dict = {
        "match[status_uuid]": params.get("status_uuid"),
        "match[status_name]": params.get("status_name"),
        "match[short_id]": params.get("short_id"),
        "match[rule_uuid]": params.get("rule_uuid"),
        "match[rule_name]": params.get("rule_name"),
        "date[created_at]": created_at,
    }

    try:
        response: dict = GenericAPIAction(config, "get", url, params=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
