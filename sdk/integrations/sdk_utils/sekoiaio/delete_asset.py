from urllib.parse import urljoin

from connectors.core.base_connector import ConnectorError
from sdk_utils.sekoiaio.constants import ASSETS_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction


def delete_asset(config, params):
    """
    Delete a specific asset
    """
    url: str = urljoin(ASSETS_BASE_URL, f"assets/{params['asset_uuid']}")

    try:
        response = GenericAPIAction(config, "DELETE", url).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
