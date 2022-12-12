from connectors.core.connector import get_logger, ConnectorError
from sdk_utils.sekoiaio.constants import OPERATION_CENTER_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction

logger = get_logger("connector_name")


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
