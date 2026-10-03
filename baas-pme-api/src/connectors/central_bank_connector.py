from decimal import Decimal

from connectors.rest_connector import RestConnector
from constants import CENTRAL_BANK_API_TIMEOUT, CENTRAL_BANK_API_URL
from errors import ExternalConnectorError


class CentralBankConnector(RestConnector):
    """Cliente da consulta de taxa acumulada de IPCA ou IGPM."""

    def __init__(self) -> None:
        super().__init__(__name__, CENTRAL_BANK_API_URL, CENTRAL_BANK_API_TIMEOUT)

    def get_accumulated_rate(self, index_code: str) -> Decimal:
        body = self.request_json(endpoint=f"/index/{index_code}", method="GET")
        rate = body.get("accumulated_rate")

        if body.get("index") != index_code or type(rate) not in (str, int, Decimal):
            raise ExternalConnectorError(self.__class__.__name__)

        try:
            decimal_rate = Decimal(str(rate))
        except (ValueError, ArithmeticError) as error:
            raise ExternalConnectorError(self.__class__.__name__) from error

        if not decimal_rate.is_finite():
            raise ExternalConnectorError(self.__class__.__name__)

        return decimal_rate
