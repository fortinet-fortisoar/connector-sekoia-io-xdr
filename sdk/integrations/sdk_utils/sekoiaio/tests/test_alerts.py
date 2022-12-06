import os
from unittest import TestCase
from unittest.mock import patch

from django.conf import settings


class AlertsTestCase(TestCase):
    conf: dict = {
        "api_key": os.getenv("api_key"),
        "verify_certificate": True,
        "proxy": True,
    }

    def test_get_alert(self):
        settings.configure()
        from sdk_utils.sekoiaio.get_alert import get_alert

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "operation": None,
                "status": "Success",
                "message": "",
                "data": {
                    "history": [
                        {
                            "alert_type": {
                                "previous_category": None,
                                "previous_value": None,
                                "value": "system-compromise",
                                "category": "intrusions",
                            },
                            "created_by": "59899459-d385-48da-9c0e-1d91ebe42c4a",
                            "created_by_type": "application",
                            "entry_type": "alert_type",
                            "created_at": 1669676732,
                            "history_comments": [],
                            "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                        },
                        {
                            "created_by": "59899459-d385-48da-9c0e-1d91ebe42c4a",
                            "created_by_type": "application",
                            "entry_type": "urgency",
                            "created_at": 1669676732,
                            "urgency": {"previous_value": None, "value": 30},
                            "history_comments": [],
                            "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                        },
                        {
                            "alert": {"status": "Pending", "previous_status": None},
                            "created_by": "59899459-d385-48da-9c0e-1d91ebe42c4a",
                            "created_by_type": "application",
                            "entry_type": "alert",
                            "created_at": 1669676732,
                            "history_comments": [],
                            "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                        },
                    ],
                    "created_by": "59899459-d385-48da-9c0e-1d91ebe42c4a",
                    "first_seen_at": "2022-11-28T21:00:00+00:00",
                    "entity": {
                        "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                        "name": "Information Technology Paris site",
                    },
                    "similar": 1,
                    "created_at": 1669676732,
                    "urgency": {
                        "display": "Moderate",
                        "severity": 30,
                        "value": 30,
                        "current_value": 30,
                        "criticity": 0,
                    },
                    "community_uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                    "source": None,
                    "ttps": [],
                    "countermeasures": [],
                    "title": "Abnormal OpenSSH log volume",
                    "number_of_unseen_comments": 0,
                    "created_by_type": "application",
                    "assets": [],
                    "updated_by_type": "application",
                    "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                    "comments": [],
                    "rule": {
                        "severity": 30,
                        "description": "",
                        "type": "anomaly",
                        "name": "Abnormal OpenSSH log volume",
                        "pattern": "",
                        "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                    },
                    "alert_type": {
                        "value": "system-compromise",
                        "category": "intrusions",
                    },
                    "details": "",
                    "target": None,
                    "updated_by": "59899459-d385-48da-9c0e-1d91ebe42c4a",
                    "short_id": "ALfghiw34ax",
                    "updated_at": 1670101532,
                    "status": {
                        "description": "The alert is waiting for action",
                        "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                        "name": "Pending",
                    },
                    "last_seen_at": "2022-12-03T21:05:32.307177+00:00",
                    "similarity_strategy": None,
                    "kill_chain_short_id": None,
                    "adversaries": [],
                    "stix": {
                        "id": "5e74a541-c265-4995-9b58-cc7d1e74aa44",
                        "type": "bundle",
                        "objects": [
                            {
                                "id": "identity--7f7676e7-a254-43c3-acf6-1b920a94fe51",
                                "name": "Information Technology Paris site",
                                "type": "identity",
                                "created": "2022-11-28T23:05:31.408025Z",
                                "modified": "2022-11-28T23:05:31.408025Z",
                                "description": "",
                                "x_sic_site_id": "",
                                "identity_class": "entity",
                            },
                        ],
                        "spec_version": "2.0",
                    },
                },
                "env": {},
            }

            result = get_alert(config=self.conf, params={"alert_uuid": "ALfghiw34ax"})

            assert result is not None
            assert query.call_count == 1
            assert "data" in result
            assert result["data"] is not None

    def test_list_alerts(self):
        pass

    def test_update_alert_status(self):
        settings.configure()
        from sdk_utils.sekoiaio.update_alert_status import (
            ACTION_VALIDATE,
            update_alert_status,
        )

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = 200

            result = update_alert_status(
                config=self.conf,
                params={
                    "alert_uuid": "Ahytv57q55F",
                    "comment": "Validate",
                    "action_uuid": ACTION_VALIDATE.uuid,
                },
            )
            assert result == 200

    def test_add_comment_to_alert(self):
        settings.configure()
        from sdk_utils.sekoiaio.add_comment_to_alert import add_comment_to_alert

        with patch(f"sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            query.return_value = {
                "unseen": False,
                "created_by_type": "apikey",
                "date": 1670309132,
                "uuid": "fbdeaba1-dd63-496f-b515-9f14a886a51a",
                "author": "ydi",
                "created_by": "a2f80bf3-93a0-485d-b3db-51611825474c",
                "content": "New comment test",
            }
            result = add_comment_to_alert(
                config=self.conf,
                params={
                    "alert_uuid": "ALfghiw34ax",
                    "comment": "New comment test",
                    "author": "ydi",
                },
            )
            assert result is not None
            assert "uuid" in result
