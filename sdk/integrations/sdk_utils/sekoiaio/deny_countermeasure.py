from urllib.parse import urljoin

from connectors.core.base_connector import ConnectorError
from sdk_utils.sekoiaio.constants import OPERATION_CENTER_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction


def deny_countermeasure(config, params):
    """
    Deny a countermeasure
    """
    url: str = urljoin(OPERATION_CENTER_BASE_URL, f"countermeasures/{params['countermeasure_uuid']}/deny")
    data: dict = {
        "comment": {"content": params["content"], "author": params.get("author")}
    }

    try:
        response = GenericAPIAction(config, "PATCH", url, json=data).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response