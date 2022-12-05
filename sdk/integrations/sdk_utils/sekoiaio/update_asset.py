from urllib.parse import urljoin

from connectors.core.base_connector import ConnectorError
from sdk_utils.sekoiaio.constants import ASSETS_BASE_URL
from sdk_utils.sekoiaio.utils import GenericAPIAction


def update_asset(config, params):
    """
    Update a specific asset
    """
    url: str = urljoin(ASSETS_BASE_URL, f"assets/{params['asset_uuid']}")
    payload: dict = {
        "asset_type": params["asset_type"],
        "name": params.get("name", None),
        "description": params.get("description", None),
        "criticity": params.get("criticity", None),
        "attributes": params.get("attributes", None),
        "keys": params.get("keys", None),
        "owners": params.get("owners", None),
    }

    try:
        response = GenericAPIAction(config, "PUT", url, json=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response