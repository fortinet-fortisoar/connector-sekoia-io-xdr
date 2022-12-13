from connectors.core.base_connector import ConnectorError

from .constants import ASSETS_BASE_URL
from .utils import GenericAPIAction


def update_asset(config, params):
    """
    Update a specific asset
    """

    url: str = f"{ASSETS_BASE_URL}/{params['asset_uuid']}"
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
