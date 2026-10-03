from connectors.rest_connector import RestConnector
from constants import BANKSLIP_API_TIMEOUT, BANKSLIP_API_URL
from errors import ExternalConnectorError


class BankSlipConnector(RestConnector):
    """Cliente do contrato externo de emissao em lote de boletos."""

    def __init__(self) -> None:
        super().__init__(__name__, BANKSLIP_API_URL, BANKSLIP_API_TIMEOUT)

    def issue_batch(self, external_reference: str, installments: list[dict]) -> list[dict]:
        body = self.request_json(
            endpoint="/bank-slips",
            method="POST",
            payload={"external_reference": external_reference, "installments": installments},
        )
        bank_slips = body.get("bank_slips")

        if not isinstance(bank_slips, list):
            raise ExternalConnectorError(self.__class__.__name__)

        for bank_slip in bank_slips:
            if not isinstance(bank_slip, dict) or type(bank_slip.get("installment_number")) is not int:
                raise ExternalConnectorError(self.__class__.__name__)
            if not isinstance(bank_slip.get("barcode"), str) or not bank_slip["barcode"]:
                raise ExternalConnectorError(self.__class__.__name__)

        return bank_slips
