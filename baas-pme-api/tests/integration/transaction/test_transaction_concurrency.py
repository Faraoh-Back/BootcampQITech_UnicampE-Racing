from collections import Counter
from os import environ
from uuid import uuid4

import pytest
import requests

from tests.utils.concurrency import run_parallel
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


def _post_withdrawal(session: requests.Session, account_key: str, amount: int) -> tuple[int, dict]:
    host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    port = environ.get("API_PORT", "3000")
    response = session.post(
        f"http://{host}:{port}/account/{account_key}/transaction",
        json={"type": "WITHDRAWAL", "amount": amount},
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": str(uuid4())},
        timeout=10,
    )
    return response.status_code, response.json()


class TestTransactionConcurrency:
    @pytest.mark.parametrize("_attempt", range(5))
    def test_two_withdrawals_compete_for_the_last_available_balance(self, make_account, _attempt):
        account_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 201

        results = run_parallel(2, lambda session: _post_withdrawal(session, account_key, 80))

        assert Counter(status for status, _ in results) == Counter({201: 1, 422: 1})
        failed_response = next(body for status, body in results if status == 422)
        assert failed_response["code"] == "QIT001005"
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 20
        status, statement = RequestGenerator.GET_transactions(
            account_key, {"type": "WITHDRAWAL", "limit": 10}
        )
        assert status == 200
        assert len(statement["data"]) == 1
        assert statement["data"][0]["amount"] == -80

    @pytest.mark.parametrize("_attempt", range(5))
    def test_ten_withdrawals_leave_only_the_three_that_fit(self, make_account, _attempt):
        account_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 201

        results = run_parallel(10, lambda session: _post_withdrawal(session, account_key, 30))

        assert Counter(status for status, _ in results) == Counter({201: 3, 422: 7})
        assert all(body["code"] == "QIT001005" for status, body in results if status == 422)
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 10
        status, statement = RequestGenerator.GET_transactions(
            account_key, {"type": "WITHDRAWAL", "limit": 10}
        )
        assert status == 200
        assert len(statement["data"]) == 3
        assert sum(entry["amount"] for entry in statement["data"]) == -90
