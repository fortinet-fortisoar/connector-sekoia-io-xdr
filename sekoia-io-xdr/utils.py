import time
from urllib.parse import urljoin

import requests
from requests import Response, Session, Timeout
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from urllib3.util.retry import Retry

from connectors.core.connector import get_logger
from .constants import BASE_URL, INTEGRATION_NAME

logger = get_logger("sekoia-io-xdr")


class GenericAPIAction:
    def __init__(self, config, verb: str, url: str, timeout: int = 5, **kwargs):
        self._verb = verb
        self._config = config
        self._url = url
        self._timeout = timeout
        self.request_kwargs = kwargs

    @property
    def _headers(self):
        headers = {"Accept": "application/json"}
        api_key = self._config["api_key"]
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def log_request_error(self, response):
        try:
            content = response.json()
        except ValueError:
            content = response.content
        logger.error(
            "HTTP Request failed: {0} with {1} {2}".format(
                self._url, response.status_code, content
            )
        )

    def log_timeout_error(self):
        logger.error("HTTP Request timeout: {0}".format(self._url))

    def run(self):
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(5),
                wait=wait_exponential(multiplier=2, min=1, max=10),
                retry=retry_if_exception_type(Timeout),
            ):
                with attempt:
                    response: Response = requests.request(
                        self._verb,
                        self._url,
                        headers=self._headers,
                        timeout=self._timeout,
                        **self.request_kwargs,
                    )
        except RetryError:
            self.log_timeout_error()
            return None

        if not response.ok:
            self.log_request_error(response)
            return None

        return response.json()


class Client:
    """Client class to interact with the SEKOIA.IO API"""

    def __init__(self, headers: dict, verify: bool = False, proxy: bool = False):
        self._headers = headers
        self.verify = verify
        self.proxy = proxy
        self.url = urljoin(BASE_URL, "/v1/apiauth/auth/validate")

    def get_validate_resource(self) -> str:
        """
        Validate the API Key against SEKOIA.IO API
        """
        response = requests.get(
            self.url, headers=self._headers, verify=self.verify, proxies=self.proxy
        )

        if (
            "message" in response.json()
            and response.json()["message"] == "The token is invalid"
        ):
            raise Exception(
                f"{INTEGRATION_NAME} error: the request failed due to: {response}"
            )

        return "ok"


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
