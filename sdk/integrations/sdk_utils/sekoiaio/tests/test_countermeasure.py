import os
import django
from unittest import TestCase
from unittest.mock import patch
from django.conf import settings

from sdk_utils.sekoiaio.activate_countermeasure import activate_countermeasure


class CountermeasuresTestCase(TestCase):
    config: dict = {
        "api_key": "eyJhbGciOiJQUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY2OTI4NTc0MSwianRpIjoiOTdhMjFiYWItZGVjMi00MTQ1LWE4ZTgtZmNlNDEzNmQyNmU5IiwidHlwZSI6ImFjY2VzcyIsImlkZW50aXR5IjoiYXBpa2V5OmEyZjgwYmYzLTkzYTAtNDg1ZC1iM2RiLTUxNjExODI1NDc0YyIsIm5iZiI6MTY2OTI4NTc0MSwiY3NyZiI6IjJjODRhZWIyLWE5ODItNDQ1MC05N2U5LWU1Yzk4ZjkyZjExZiJ9.gDxtreXT6PRTmjfpBT-3EknLRg51Xpkao_yt2p5PsiRDtxL3OdLBg8f9lg6LRmSl1ySqic0dmGMf5UiJD3IyN_0V7YALo0z152sJLyh-zaTwiLk6DbNp2OclYh3BxlFY2Kgzsgxyon77GiBOSmEI9tFsyze1dz0N1BZYxvoAucri4XpO-UWK795j0LfQRLs3-wcbwM4mIRIEfVN0VI7qVI29i3aQVPNN2YD9Yxe-iczanf0EK4eMTxnHmP26Nbx57MSkq5xSHE2n3gEV41WRoI9Qwa3lEmWc1d8vIzbA8vR2GEpTkGdX1NnAv5HCxZd2h1wm9WigEvBviu1jiV8u_8q8xKu-mezvkFsZu7q8gXQyBoXIqvbbLotVHbzhhvbi130gWJpE8UmDSI7LfAht42qyq95Ozbe0moAv71UmPvQ9hMXnm4mJEaeZX4xDa34EvslkjX83T6zHIlVUzi7DlgQKzlWMTdVi_EvPSHnlm1-khrm3JIWUoEnPOvmTDBJ0iRQVeL7iEjaT7robBoxb_7j7ZJ_e0k50ePPnOt7P7c8DU-f1HCHD_oYT8ILdh9ZKh8JBTD9pTnc9fIL_2mXESon_7TKZQM88RpByUyBUx8g1WG_5J5cYvOXqdoUH4-AyMaKKUCVZlDLnDiDFqmdYF0rUwzKLl918GfQEAcWdlOQ",
        "verify_certificate": True,
        "proxy": True
    }
    settings.configure()

    def test_activate_countermeasure(self):
        print("éoijazfpj")
        os.environ.setdefault("settings.DJANGO_ROOT", "/Users/yosradirgham/Desktop/fortisoar/connector-sekoia-io-xdr/sdk/integrations")
        settings.configure()
        with patch("sdk_utils.sekoiaio.utils.GenericAPIAction.run") as query:
            settings.configure()
            print(f'settings.DJANGO_ROOT = {settings.DJANGO_ROOT}')
            print(f'settings.DJANGO_ROOT = {settings.DJANGO_ROOT}')
            print('--------')
            print(f'query = {query}')
            assert 1 == 1
            result = activate_countermeasure(config=self.config, params={"content": "", "author": ""})
            print(f'result = {result}')

    def test_deny_countermeasure(self):
        pass
