import re
from os import environ
from uuid import uuid4

import pytest
import requests

from tests.utils.mock_server import expect_bankslip_status, reset
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


def _metrics() -> str:
    response = requests.get(
        f"http://{environ.get('SERVER_LOCALHOST', '0.0.0.0')}:{environ.get('API_PORT', '3000')}/metrics",
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        timeout=3,
    )
    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]
    return response.text


def _counter_value(metrics: str, name: str, labels: str) -> float:
    match = re.search(rf"^{re.escape(name)}\{{{re.escape(labels)}\}} ([0-9.e+-]+)$", metrics, re.MULTILINE)
    return float(match.group(1)) if match else 0.0


def _gauge_value(metrics: str, name: str) -> float:
    match = re.search(rf"^{re.escape(name)} ([0-9.e+-]+)$", metrics, re.MULTILINE)
    return float(match.group(1)) if match else 0.0


class TestMetrics:
    @pytest.fixture(autouse=True)
    def reset_mockserver(self):
        reset()
        yield
        reset()

    def test_exposes_safe_http_metrics_and_counts_idempotency_replay(self, make_account):
        before = _counter_value(
            _metrics(), "baas_idempotency_replays_total", 'scope="transaction"'
        )
        account_key = make_account()["response"]["account_key"]
        key = str(uuid4())
        payload = {"type": "DEPOSIT", "amount": 100}
        assert RequestGenerator.POST_transaction(account_key, payload, idempotency_key=key)[0] == 201
        assert RequestGenerator.POST_transaction(account_key, payload, idempotency_key=key)[0] == 201

        metrics = _metrics()
        assert _counter_value(
            metrics, "baas_idempotency_replays_total", 'scope="transaction"'
        ) == before + 1
        assert 'baas_http_requests_total{method="POST",route="/account/{account_key}/transaction",status="201"}' in metrics
        assert "baas_http_request_duration_seconds" in metrics
        assert "baas_active_user_sessions" in metrics
        assert account_key not in metrics

    def test_counts_connector_failure_and_preserves_request_correlation(self, make_account):
        before = _counter_value(
            _metrics(), "baas_external_connector_failures_total", 'connector="BankSlipConnector"'
        )
        account_key = make_account()["response"]["account_key"]
        expect_bankslip_status(500)
        request_id = "metrics-correlation-01"
        response = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/billing-plan",
            payload={"base_amount": 1000, "first_due_date": "2027-01-31"},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "X-Request-ID": request_id},
        )
        assert response.response_status == 502
        assert response.response_json["code"] == "QIT001009"
        assert response.response.headers["X-Request-ID"] == request_id

        metrics = _metrics()
        assert _counter_value(
            metrics, "baas_external_connector_failures_total", 'connector="BankSlipConnector"'
        ) == before + 1
        assert 'baas_qit_errors_total{code="QIT001009",route="/account/{account_key}/billing-plan"}' in metrics

    def test_reports_active_sessions_from_the_database(self, make_customer):
        before = _gauge_value(_metrics(), "baas_active_user_sessions")
        customer_key = make_customer()["response"]["customer_key"]
        email = f"metrics-{uuid4()}@example.com"
        assert RequestGenerator.POST_user(
            {
                "customer_key": customer_key,
                "name": "Usuário de Métricas",
                "email": email,
                "password": "senha-segura-123",
            }
        )[0] == 201
        assert RequestGenerator.POST_auth_login(
            {"email": email, "password": "senha-segura-123"}
        )[0] == 201
        assert _gauge_value(_metrics(), "baas_active_user_sessions") == before + 1
