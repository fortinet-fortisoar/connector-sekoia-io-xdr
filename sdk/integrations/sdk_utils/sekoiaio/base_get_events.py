import time
from urllib.parse import urljoin

from requests import Session
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from urllib3.util.retry import Retry

from sdk_utils.sekoiaio.constants import BASE_URL


class BaseGetEvents:
    http_session: Session
    events_api_path: str

    def __init__(self, config):
        self._config = config
        self.events_api_path = urljoin(BASE_URL, "/api/v1/sic/conf/events")

    def configure_http_session(self) -> Session:
        # Configure http with retry strategy
        retry_strategy = Retry(
            total=0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.http_session = Session()
        self.http_session.mount("https://", adapter)
        self.http_session.mount("http://", adapter)
        self.http_session.headers = CaseInsensitiveDict(
            data={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._config['api_key']}",
            }
        )
        return self.http_session

    def trigger_event_search_job(
        self, query: str, earliest_time: str, latest_time: str
    ) -> str:
        response_start = self.http_session.post(
            f"{self.events_api_path}/search/jobs",
            json={
                "term": query,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "visible": False,
            },
        )
        response_start.raise_for_status()

        return response_start.json()["uuid"]

    def wait_for_search_job_execution(self, event_search_job_uuid: str) -> None:
        # wait at most 300 sec for the event search job to conclude
        max_wait_search = 300
        start_wait = time.time()

        response_get = self.http_session.get(
            f"{self.events_api_path}/search/jobs/{event_search_job_uuid}"
        )
        response_get.raise_for_status()

        while response_get.json()["status"] != 2:
            time.sleep(1)
            response_get = self.http_session.get(
                f"{self.events_api_path}/search/jobs/{event_search_job_uuid}"
            )
            response_get.raise_for_status()
            if time.time() - start_wait > max_wait_search:
                raise TimeoutError(
                    f"Event search job took more than {max_wait_search}s to conclude"
                )
