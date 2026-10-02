from os import environ
from typing import Optional, Tuple
from uuid import uuid4

from tests.utils.requisition import ClientRequisition, BaseConnectorResponse


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")


class RequestGenerator:
    # ── MÉTODOS AUXILIARES ─────────────────────────────────────────
    @staticmethod
    def _default_headers(
        custom_headers: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if custom_headers:
            headers.update(custom_headers)
        return headers

    # ── CLIENTES (/customer) ───────────────────────────────────────
    @staticmethod
    def POST_customer(payload: dict, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("POST", "/customer", payload=payload, headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def GET_customer(customer_key: str, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("GET", f"/customer/{customer_key}", headers=h)
        return res.response_status, res.response_json

    # ── CONTAS (/account) ──────────────────────────────────────────
    @staticmethod
    def POST_account(payload: dict, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("POST", "/account", payload=payload, headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def GET_account(account_key: str, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("GET", f"/account/{account_key}", headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def PUT_account_block(account_key: str, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("PUT", f"/account/{account_key}/block", headers=h)
        return res.response_status, res.response_json

    # ── TRANSAÇÕES (/transaction) ──────────────────────────────────
    @staticmethod
    def POST_transaction(
        account_key: str,
        payload: dict,
        idempotency_key: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> Tuple[int, dict]:
        if idempotency_key is None and (headers is None or "Idempotency-Key" not in headers):
            idempotency_key = str(uuid4())
        h = RequestGenerator._default_headers(headers, idempotency_key=idempotency_key)
        res = ClientRequisition.send("POST", f"/account/{account_key}/transaction", payload=payload, headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def GET_transaction(account_key: str, transaction_key: str, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("GET", f"/account/{account_key}/transaction/{transaction_key}", headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def GET_transactions(account_key: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("GET", f"/account/{account_key}/transactions", query_params=params, headers=h)
        return res.response_status, res.response_json

    # ── PLANO DE COBRANÇA E BOLETOS (/billing-plan) ────────────────
    @staticmethod
    def POST_billing_plan(account_key: str, payload: dict, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("POST", f"/account/{account_key}/billing-plan", payload=payload, headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def GET_billing_plan(account_key: str, plan_key: str, headers: Optional[dict] = None) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("GET", f"/account/{account_key}/billing-plan/{plan_key}", headers=h)
        return res.response_status, res.response_json

    @staticmethod
    def POST_billing_plan_adjustment(
        account_key: str, plan_key: str, payload: dict, headers: Optional[dict] = None
    ) -> Tuple[int, dict]:
        h = RequestGenerator._default_headers(headers)
        res = ClientRequisition.send("POST", f"/account/{account_key}/billing-plan/{plan_key}/adjustment", payload=payload, headers=h)
        return res.response_status, res.response_json

    # ── ANTECIPAÇÃO DE RECEBÍVEIS (/credit-advance) ────────────────
    @staticmethod
    def POST_credit_advance(
        account_key: str,
        payload: dict,
        idempotency_key: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> Tuple[int, dict]:
        if idempotency_key is None and (headers is None or "Idempotency-Key" not in headers):
            idempotency_key = str(uuid4())
        h = RequestGenerator._default_headers(headers, idempotency_key=idempotency_key)
        res = ClientRequisition.send("POST", f"/account/{account_key}/credit-advance", payload=payload, headers=h)
        return res.response_status, res.response_json

    # ── LEGADO / SAMPLE ENTITY ────────────────────────────────────
    @staticmethod
    def POST_sample_entity(sample_entity_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/sample_entity",
            payload=sample_entity_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_sample_entity(sample_entity_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/sample_entity/{sample_entity_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def PUT_sample_entity(sample_entity_key: str, update_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PUT",
            f"/sample_entity/{sample_entity_key}",
            payload=update_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def PUT_webhook_sample_entity(sample_entity_key: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PUT",
            f"/webhook/sample_entity/{sample_entity_key}/increment_counter",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_sample_entities(params: dict = None) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET", "/sample_entities", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}, query_params=params
        )
        return response.response_status, response.response_json
