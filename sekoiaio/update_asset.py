from connectors.core.base_connector import ConnectorError

from .constants import ASSETS_BASE_URL
from .utils import GenericAPIAction


def update_asset(config, params):
    """
    Update a specific asset
    """
    
    url: str = f"{ASSETS_BASE_URL}/{params['asset_uuid']}"
    attributes: list = list(params.get("asset_attributes").split(",")) if params.get("asset_attributes") else []
    keys: list = list(params.get("asset_keys").split(",")) if params.get("asset_keys") else []
    owners: list = list(params.get("asset_owners").split(",")) if params.get("asset_owners") else []
    
    payload: dict = {
        "asset_type": {"uuid": params["asset_type_uuid"], "name": params["asset_type_name"]},
        "name": params.get("asset_name", None),
        "description": params.get("asset_description") or "",
        "criticity": params.get("asset_criticity", None),
        "attributes": attributes,
        "keys": keys,
        "owners": owners,
    }
    
    try:
        response = GenericAPIAction(config, "PUT", url, json=payload).run()
    except Exception as e:
        raise ConnectorError(f"Error: {e}")

    return response
