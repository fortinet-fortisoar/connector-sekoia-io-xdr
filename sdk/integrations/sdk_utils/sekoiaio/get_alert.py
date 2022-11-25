from connectors.core.connector import ConnectorError, get_logger
from sdk_utils.sekoiaio.utils import GenericAPIAction

logger = get_logger("connector_name")


def get_alert(config, params):
    """
    Retrieve a specific alert
    """
    endpoint = f"alerts/{params.alert_uuid}"
    payload = {
        "stix": params.get("stix", False),
        "comments": params.get("comments", True),
        "history": params.get("history", True),
        "countermeasures": params.get("countermeasures", True),
    }
    try:
        response = GenericAPIAction(config, "get", endpoint, params=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
