from connectors.core.connector import ConnectorError, get_logger

from .constants import ASSETS_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")


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
