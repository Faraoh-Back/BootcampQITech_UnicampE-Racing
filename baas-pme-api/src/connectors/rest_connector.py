import json
import time
from decimal import Decimal

import requests

from errors import ExternalConnectorError
from utils.logger import get_logger


class RestConnector:
    """Base para chamadas a APIs externas.

    APIs externas nao recebem automaticamente o ``INTERNAL-TOKEN`` da nossa
    API. Caso algum servico interno precise dele, o conector correspondente
    deve inclui-lo explicitamente no contrato.
    """

    def __init__(self, class_name: str, base_url: str, timeout: int = 5) -> None:
        self.logger = get_logger(class_name)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request_json(self, endpoint: str, method: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        self.logger.info(f"OUTGOING REQUEST {method.upper()} {url}")
        started_at = time.perf_counter()

        try:
            response = requests.request(method.upper(), url, json=payload, timeout=self.timeout)
        except requests.RequestException as error:
            self.logger.warning(f"EXTERNAL REQUEST FAILED {method.upper()} {url}: {error}")
            raise ExternalConnectorError(self.__class__.__name__) from error

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        self.logger.info(f"INCOMING RESPONSE {response.status_code} {method.upper()} {url} - {elapsed_ms:.1f} ms")

        if response.status_code != 200:
            raise ExternalConnectorError(self.__class__.__name__)

        try:
            body = json.loads(response.content, parse_float=Decimal)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ExternalConnectorError(self.__class__.__name__) from error

        if not isinstance(body, dict):
            raise ExternalConnectorError(self.__class__.__name__)

        return body
