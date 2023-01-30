from connectors.core.connector import ConnectorError, get_logger

from .constants import ASSETS_BASE_URL
from .utils import GenericAPIAction

logger = get_logger("sekoia-io-xdr")

def delete_asset(config, params):
    """
    Delete a specific asset
    """
    url: str = f"{ASSETS_BASE_URL}/{params['asset_uuid']}"

    try:
        response = GenericAPIAction(config, "DELETE", url).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
