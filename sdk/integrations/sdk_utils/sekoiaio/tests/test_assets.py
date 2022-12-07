import os

from unittest import TestCase
from unittest.mock import patch
from django.conf import settings


class AssetsTestCase(TestCase):
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
        settings.configure()
        from sdk_utils.sekoiaio.update_asset import update_asset

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "uuid": "d4e84f5a-877a-41e8-8166-9691a9ecffa3",
                "name": "test update 1",
                "category": "",
                "description": "",
                "criticity": 23,
                "asset_type": "host",
                "community_uuid": "2783b458-fa16-4869-a11e-6e9d505beb24",
                "owners": [],
                "key_characteristics": [],
                "attributes": [{"name": "custome attr for test", "value": "testValue"}],
                "created_at": "2022-12-06T10:00:00Z",
                "updated_at": "2022-12-06T11:00:00Z",
            }
            result = update_asset(
                config=self.conf,
                params={
                    "asset_type": {
                        "uuid": "bd64a9d9-a1d6-45ba-979d-d9dc23f12f92",
                        "name": "host",
                    },
                    "asset_uuid": "d4e84f5a-877a-41e8-8166-9691a9ecffa3",
                    "name": "test update 1",
                    "criticity": 23,
                },
            )
            assert result is not None
            assert result["uuid"] == "d4e84f5a-877a-41e8-8166-9691a9ecffa3"

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
