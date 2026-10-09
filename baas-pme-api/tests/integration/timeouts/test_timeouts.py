from os import environ
from concurrent.futures import ThreadPoolExecutor
import time
from uuid import uuid4

import psycopg2
import pytest
import requests

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


def _database_connection():
    url = environ.get(
        "DATABASE_URL", "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"
    )
    return psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1))


def _api_url(path: str) -> str:
    return f"http://{environ.get('SERVER_LOCALHOST', '0.0.0.0')}:{environ.get('API_PORT', '3000')}{path}"


class TestTimeoutPolicy:
    def test_lock_timeout_returns_retryable_qit_error_with_request_id(self, make_account):
        account_key = make_account()["response"]["account_key"]
        request_id = "s14-lock-timeout-01"
        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM account WHERE account_key = %s FOR UPDATE", (account_key,))
                response = ClientRequisition.send(
                    "POST",
                    f"/account/{account_key}/transaction",
                    payload={"type": "DEPOSIT", "amount": 100},
                    headers={
                        "INTERNAL-TOKEN": INTERNAL_TOKEN,
                        "Idempotency-Key": str(uuid4()),
                        "X-Request-ID": request_id,
                    },
                )
                assert response.response_status == 503
                assert response.response_json["code"] == "QIT001024"
                assert response.response.headers["X-Request-ID"] == request_id
                connection.rollback()

    def test_long_account_lock_does_not_block_an_unrelated_request(self, make_account):
        locked_account_key = make_account()["response"]["account_key"]
        unrelated_account_key = make_account()["response"]["account_key"]

        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM account WHERE account_key = %s FOR UPDATE",
                    (locked_account_key,),
                )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    blocked_request = executor.submit(
                        ClientRequisition.send,
                        "POST",
                        f"/account/{locked_account_key}/transaction",
                        {"type": "DEPOSIT", "amount": 100},
                        {
                            "INTERNAL-TOKEN": INTERNAL_TOKEN,
                            "Idempotency-Key": str(uuid4()),
                            "X-Request-ID": "s14-worker-isolation-01",
                        },
                    )
                    # A primeira requisição aguarda a trava; uma conta sem a
                    # mesma disputa deve continuar atendida por outro worker.
                    time.sleep(0.1)
                    started_at = time.monotonic()
                    status, _ = RequestGenerator.GET_account(unrelated_account_key)
                    assert status == 200
                    assert time.monotonic() - started_at < 1

                    response = blocked_request.result(timeout=4)
                    assert response.response_status == 503
                    assert response.response_json["code"] == "QIT001024"
                connection.rollback()

    def test_client_interruption_replays_exactly_once_with_same_idempotency_key(self, make_account):
        account_key = make_account()["response"]["account_key"]
        idempotency_key = str(uuid4())
        payload = {"type": "DEPOSIT", "amount": 100}
        headers = {
            "INTERNAL-TOKEN": INTERNAL_TOKEN,
            "Idempotency-Key": idempotency_key,
            "X-Request-ID": "s14-client-interrupted-01",
        }

        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM account WHERE account_key = %s FOR UPDATE", (account_key,))
                with pytest.raises(requests.ReadTimeout):
                    requests.post(
                        _api_url(f"/account/{account_key}/transaction"),
                        json=payload,
                        headers=headers,
                        timeout=0.1,
                    )
                # A primeira requisição ainda pode estar esperando a trava;
                # soltar a trava simula o servidor concluir depois de o cliente
                # ter desistido de esperar pela resposta.
                connection.rollback()

        deadline = time.monotonic() + 4
        while True:
            status, replay = RequestGenerator.POST_transaction(
                account_key, payload, idempotency_key=idempotency_key
            )
            if status == 201:
                break
            assert time.monotonic() < deadline, replay
            time.sleep(0.05)

        assert replay["amount"] == 100
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 100
        status, statement = RequestGenerator.GET_transactions(account_key)
        assert status == 200
        assert len(statement["data"]) == 1
