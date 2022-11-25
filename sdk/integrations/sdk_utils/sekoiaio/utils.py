from urllib.parse import urljoin

import requests
from connectors.core.connector import get_logger
from requests import Response, Timeout
from sdk_utils.sekoiaio.constants import BASE_URL, INTEGRATION_NAME
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = get_logger("connector_name")


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
