"""Cenários de concorrência cruzada exercitados exclusivamente por HTTP."""

from collections import Counter
from os import environ
from queue import SimpleQueue
from uuid import uuid4

import pytest
import requests

from tests.utils.concurrency import run_parallel
from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


def _api_url(path: str) -> str:
    host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    port = environ.get("API_PORT", "3000")
    return f"http://{host}:{port}{path}"


def _post_transaction(
    session: requests.Session, account_key: str, payload: dict, idempotency_key: str
) -> tuple[int, dict]:
    response = session.post(
        _api_url(f"/account/{account_key}/transaction"),
        json=payload,
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": idempotency_key},
        timeout=30,
    )
    return response.status_code, response.json()


def _post_credit_advance(
    session: requests.Session, account_key: str, bank_slip_key: str
) -> tuple[int, dict]:
    response = session.post(
        _api_url(f"/account/{account_key}/credit-advance"),
        json={"bank_slip_keys": [bank_slip_key]},
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": str(uuid4())},
        timeout=30,
    )
    return response.status_code, response.json()


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


class TestAdvancedConcurrency:
    @pytest.mark.parametrize("_attempt", range(5))
    def test_cross_transfers_finish_without_deadlock_and_preserve_total_minus_fees(
        self, make_account, _attempt
    ):
        origin_key = make_account()["response"]["account_key"]
        destination_key = make_account()["response"]["account_key"]
        for account_key in (origin_key, destination_key):
            status, _ = RequestGenerator.POST_transaction(
                account_key, {"type": "DEPOSIT", "amount": 10000}
            )
            assert status == 201

        directions: SimpleQueue[tuple[str, str]] = SimpleQueue()
        for _ in range(20):
            directions.put((origin_key, destination_key))
            directions.put((destination_key, origin_key))

        def transfer(session: requests.Session) -> tuple[int, dict]:
            origin, destination = directions.get_nowait()
            return _post_transaction(
                session,
                origin,
                {"type": "TRANSFER", "amount": 100, "destination_account_key": destination},
                str(uuid4()),
            )

        results = run_parallel(40, transfer, timeout_seconds=30)
        assert Counter(status for status, _ in results) == Counter({201: 40})

        status, origin = RequestGenerator.GET_account(origin_key)
        assert status == 200
        status, destination = RequestGenerator.GET_account(destination_key)
        assert status == 200
        assert origin["balance"] + destination["balance"] == 20000 - (40 * 100)

    @pytest.mark.parametrize("_attempt", range(5))
    def test_same_idempotency_key_in_ten_threads_creates_one_ledger_group(
        self, make_account, _attempt
    ):
        account_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 1000}
        )
        assert status == 201

        idempotency_key = str(uuid4())
        payload = {"type": "WITHDRAWAL", "amount": 100}
        results = run_parallel(
            10,
            lambda session: _post_transaction(session, account_key, payload, idempotency_key),
            timeout_seconds=30,
        )

        assert Counter(status for status, _ in results) == Counter({201: 10})
        assert len({body["transaction_key"] for _, body in results}) == 1
        status, statement = RequestGenerator.GET_transactions(
            account_key, {"type": "WITHDRAWAL", "limit": 10}
        )
        assert status == 200
        assert len(statement["data"]) == 1
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 900

    @pytest.mark.parametrize("_attempt", range(5))
    def test_two_advances_of_the_same_slip_allow_only_one(self, make_account, _attempt):
        account_key = make_account()["response"]["account_key"]
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(
            account_key, {"base_amount": 10000, "first_due_date": "2027-01-31"}
        )
        assert status == 201
        bank_slip_key = plan["bank_slips"][0]["bank_slip_key"]

        results = run_parallel(
            2,
            lambda session: _post_credit_advance(session, account_key, bank_slip_key),
            timeout_seconds=30,
        )

        assert Counter(status for status, _ in results) == Counter({201: 1, 409: 1})
        assert next(body for status, body in results if status == 409)["code"] == "QIT001016"
        status, entries = RequestGenerator.GET_transactions(
            account_key, {"type": "ADVANCE_CREDIT", "limit": 10}
        )
        assert status == 200
        assert len(entries["data"]) == 1

    @pytest.mark.parametrize("_attempt", range(5))
    def test_two_transfers_competing_for_last_balance_have_one_winner(
        self, make_account, _attempt
    ):
        origin_key = make_account()["response"]["account_key"]
        first_destination_key = make_account()["response"]["account_key"]
        second_destination_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            origin_key, {"type": "DEPOSIT", "amount": 600}
        )
        assert status == 201

        destinations: SimpleQueue[str] = SimpleQueue()
        destinations.put(first_destination_key)
        destinations.put(second_destination_key)

        def transfer(session: requests.Session) -> tuple[int, dict]:
            return _post_transaction(
                session,
                origin_key,
                {
                    "type": "TRANSFER",
                    "amount": 500,
                    "destination_account_key": destinations.get_nowait(),
                },
                str(uuid4()),
            )

        results = run_parallel(2, transfer, timeout_seconds=30)
        assert Counter(status for status, _ in results) == Counter({201: 1, 422: 1})
        assert next(body for status, body in results if status == 422)["code"] == "QIT001005"
        status, account = RequestGenerator.GET_account(origin_key)
        assert status == 200
        assert account["balance"] == 0
        status, entries = RequestGenerator.GET_transactions(
            origin_key, {"type": "TRANSFER_OUT", "limit": 10}
        )
        assert status == 200
        assert len(entries["data"]) == 1
