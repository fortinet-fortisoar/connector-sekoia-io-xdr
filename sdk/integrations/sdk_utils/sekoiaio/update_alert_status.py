from urllib.parse import urljoin

from connectors.core.connector import get_logger, ConnectorError
from sdk_utils.sekoiaio.constants import OPERATION_CENTER_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction, StatusWorkflowAction

logger = get_logger("connector_name")


ACTION_ACK = StatusWorkflowAction(
    "937bdabf-6a08-434b-b6d3-d7447e4e452a", "Acknowledge", "Acknowledge the alert"
)
ACTION_VALIDATE = StatusWorkflowAction(
    "c39a0a95-aa2c-4d0d-8d2e-d3decf426eea", "Validate", "Validate the alert"
)
ACTION_REJECT = StatusWorkflowAction(
    "ade85d7b-7507-4026-bfc6-cc006d10ddac", "Reject", "Reject the alert"
)
ACTION_CLOSE = StatusWorkflowAction(
    "1390be4e-ced8-4dd6-9bed-573471b235ab", "Close", "Close the alert"
)


def _validate_action_uuid(action_uuid: str):
    return action_uuid in [
        ACTION_ACK.uuid,
        ACTION_VALIDATE.uuid,
        ACTION_REJECT.uuid,
        ACTION_CLOSE.uuid,
    ]


def update_alert_status(config, params):
    """
    Performs an action on the alert and changes the status of the alert
    according to the performed action and the workflow.
    """
    url = urljoin(OPERATION_CENTER_BASE_URL, f"alerts/{params['alert_uuid']}/workflow")
    body = {"action_uuid": params["action_uuid"], "comment": params.get("comment")}

    try:
        if _validate_action_uuid(params["action_uuid"]):
            response = GenericAPIAction(config, "PATCH", url, json=body).run()
        else:
            raise ConnectorError(f"Error: Invalid Action UUID")
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
