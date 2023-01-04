import os
from unittest import TestCase
from unittest.mock import patch
from django.conf import settings


class CountermeasuresTestCase(TestCase):
    config: dict = {
        "api_key": os.getenv("api_key"),
        "verify_certificate": True,
        "proxy": True,
    }

    def test_activate_countermeasure(self):
        settings.configure()
        from sdk_utils.sekoiaio.activate_countermeasure import activate_countermeasure

        with patch("sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "alert_uuid": "2783b458-fa16-4869-a11e-6e9d505beb24",
                "uuid": "dc2e68d2-5978-4bd8-8840-89c7453f16f5",
                "relevance": 10,
                "model_uuid": "bd64a9d9-a1d6-45ba-979d-d9dc23f12f92",
                "dynamic_relevance": 11,
                "duration": "100",
                "created_at": "2022-12-06T10:00:00Z",
                "created_by_type": "avatar",
                "activated_at": "2022-12-06T10:01:00Z",
                "activated_by": "ydi",
                "activated_by_type": "avatar",
                "denied_at": None,
                "denied_by": None,
                "denied_by_type": None,
                "action_steps": [],
                "name": "Test",
                "description": "",
                "comments": "",
                "assignee": "",
                "type": "text",
                "external_ref": "",
            }
            result = activate_countermeasure(
                config=self.config,
                params={
                    "countermeasure_uuid": "dc2e68d2-5978-4bd8-8840-89c7453f16f5",
                    "content": "bar",
                    "author": "ydi",
                },
            )

            assert result is not None
            assert "uuid" in result
            assert result["uuid"] == "dc2e68d2-5978-4bd8-8840-89c7453f16f5"
            assert result["activated_at"] is not None
            assert result["denied_at"] is None

    def test_deny_countermeasure(self):
        settings.configure()
        from sdk_utils.sekoiaio.deny_countermeasure import deny_countermeasure

        with patch("sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "alert_uuid": "2783b458-fa16-4869-a11e-6e9d505beb24",
                "uuid": "dc2e68d2-5978-4bd8-8840-89c7453f16f5",
                "relevance": 10,
                "model_uuid": "bd64a9d9-a1d6-45ba-979d-d9dc23f12f92",
                "dynamic_relevance": 11,
                "duration": "100",
                "created_at": "2022-12-06T10:00:00Z",
                "created_by_type": "avatar",
                "activated_at": None,
                "activated_by": None,
                "activated_by_type": None,
                "denied_at": "2022-12-06T10:01:00Z",
                "denied_by": "ydi",
                "denied_by_type": "avatar",
                "action_steps": [],
                "name": "Test",
                "description": "",
                "comments": "",
                "assignee": "",
                "type": "text",
                "external_ref": "",
            }
            result = deny_countermeasure(
                config=self.config,
                params={
                    "countermeasure_uuid": "dc2e68d2-5978-4bd8-8840-89c7453f16f5",
                    "content": "bar",
                    "author": "ydi",
                },
            )
            assert result is not None
            assert "uuid" in result
            assert result["uuid"] == "dc2e68d2-5978-4bd8-8840-89c7453f16f5"
            assert result["activated_at"] is None
            assert result["denied_at"] is not None
