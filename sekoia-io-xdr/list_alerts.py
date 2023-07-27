from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


def list_alerts(config, params):
    url: str = OPERATION_CENTER_BASE_URL

    if params.get("creation_start_date") or params.get("creation_end_date"):
        created_at = f"{params['creation_start_date'] or ''},{params['creation_end_date'] or ''}"
    else:
        created_at = None

    if params.get("updated_start_date") or params.get("updated_end_date"):
        updated_at = f"{params['updated_start_date'] or ''},{params['updated_end_date'] or ''}"
    else:
        updated_at = None

    payload: dict = {
        "match[status_uuid]": params.get("status_uuid"),
        "match[status_name]": params.get("status_name"),
        "match[short_id]": params.get("short_id"),
        "match[rule_uuid]": params.get("rule_uuid"),
        "match[rule_name]": params.get("rule_name"),
        "date[created_at]": created_at,
        "date[updated_at]": updated_at,
        "offset": params.get("offset") or "0",
        "limit": params.get("limit") or "100",
    }

    try:
        response: dict = GenericAPIAction(config, "get", url, params=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
