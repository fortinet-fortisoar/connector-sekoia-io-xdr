import os

from unittest import TestCase
from unittest.mock import patch
from django.conf import settings


class AssetsCaseTest(TestCase):
    conf: dict = {
        "api_key": os.getenv("api_key"),
        "verify_certificate": True,
        "proxy": True,
    }

    def test_get_asset(self):
        settings.configure()
        from sdk_utils.sekoiaio.get_asset import get_asset

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "name": "DMZ-01",
                "created_at": "2019-11-21T09:40:32.514254+00:00",
                "criticity": {"display": "high", "value": 70},
                "owners": [],
                "asset_type": {
                    "name": "network",
                    "uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460",
                },
                "keys": [
                    {
                        "name": "cidr-v4",
                        "value": "172.31.0.0/24",
                        "uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460",
                    }
                ],
                "description": "Lan with Web server and proxy",
                "attributes": [],
                "updated_at": None,
                "uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460",
                "category": {
                    "name": "technical",
                    "uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460",
                },
                "community_uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460",
            }
            asset_uuid = "82aa4cea-41fd-4381-8bb9-7100e7f97460"
            result = get_asset(config=self.conf, params={"asset_uuid": asset_uuid})
            assert result is not None
            assert result["uuid"] == asset_uuid

    def test_update_asset(self):
        pass

    def test_delete_asset(self):
        settings.configure()
        from sdk_utils.sekoiaio.delete_asset import delete_asset

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = 201
            result = delete_asset(
                config=self.conf,
                params={"asset_uuid": "82aa4cea-41fd-4381-8bb9-7100e7f97460"},
            )
            assert result is not None
