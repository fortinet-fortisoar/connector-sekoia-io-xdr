from connectors.core.connector import ConnectorError, get_logger
from sdk_utils.sekoiaio.constants import ASSETS_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction

logger = get_logger("connector_name")


def get_asset(config, params: dict):
    """
    Retrieve a specific asset
    """
    url = f"{ASSETS_BASE_URL}/{params['asset_uuid']}"

    try:
        response = GenericAPIAction(config, "GET", url).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
