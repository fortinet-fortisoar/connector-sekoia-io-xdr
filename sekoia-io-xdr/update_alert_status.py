from connectors.core.connector import ConnectorError, get_logger

from .constants import OPERATION_CENTER_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


def update_alert_status(config, params):
    """
    Performs an action on the alert and changes the status of the alert
    according to the performed action and the workflow.
    """
    url = f"{OPERATION_CENTER_BASE_URL}/{params['alert_uuid']}/workflow"
    body = {"action_uuid": params["action_uuid"], "comment": params.get("comment")}

    try:
        response = GenericAPIAction(config, "PATCH", url, json=body).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
