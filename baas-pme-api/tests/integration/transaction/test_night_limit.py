from tests.utils.request_generator import RequestGenerator
from uuid import uuid4

import pytest


class TestNightLimit:
    def test_withdrawal_allows_the_limit_rejects_one_cent_above_and_never_limits_deposits(
        self, make_account
    ):
        allowed_account_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            allowed_account_key, {"type": "DEPOSIT", "amount": 100001}
        )
        assert status == 201
        status, withdrawal = RequestGenerator.POST_transaction(
            allowed_account_key, {"type": "WITHDRAWAL", "amount": 100000}
        )
        assert status == 201
        assert withdrawal["balance"] == 1

        rejected_account_key = make_account()["response"]["account_key"]
        status, deposited = RequestGenerator.POST_transaction(
            rejected_account_key, {"type": "DEPOSIT", "amount": 100001}
        )
        assert status == 201
        assert deposited["balance"] == 100001
        status, error = RequestGenerator.POST_transaction(
            rejected_account_key, {"type": "WITHDRAWAL", "amount": 100001}
        )
        assert status == 422
        assert error["code"] == "QIT001007"
        status, account = RequestGenerator.GET_account(rejected_account_key)
        assert status == 200
        assert account["balance"] == 100001
        status, statement = RequestGenerator.GET_transactions(
            rejected_account_key, {"type": "WITHDRAWAL"}
        )
        assert status == 200
        assert statement["data"] == []

    def test_transfer_limits_the_amount_not_the_fee_and_failure_is_atomic(self, make_account):
        origin_key = make_account()["response"]["account_key"]
        destination_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            origin_key, {"type": "DEPOSIT", "amount": 100100}
        )
        assert status == 201
        status, transfer = RequestGenerator.POST_transaction(
            origin_key,
            {"type": "TRANSFER", "amount": 100000, "destination_account_key": destination_key},
        )
        assert status == 201
        assert transfer["fee_amount"] == 100
        assert transfer["balance"] == 0
        status, destination = RequestGenerator.GET_account(destination_key)
        assert status == 200
        assert destination["balance"] == 100000

        rejected_origin_key = make_account()["response"]["account_key"]
        rejected_destination_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            rejected_origin_key, {"type": "DEPOSIT", "amount": 100101}
        )
        assert status == 201
        status, error = RequestGenerator.POST_transaction(
            rejected_origin_key,
            {
                "type": "TRANSFER",
                "amount": 100001,
                "destination_account_key": rejected_destination_key,
            },
        )
        assert status == 422
        assert error["code"] == "QIT001007"
        status, origin = RequestGenerator.GET_account(rejected_origin_key)
        assert status == 200
        assert origin["balance"] == 100101
        status, destination = RequestGenerator.GET_account(rejected_destination_key)
        assert status == 200
        assert destination["balance"] == 0
        for transaction_type in ("TRANSFER_OUT", "TRANSFER_FEE"):
            status, statement = RequestGenerator.GET_transactions(
                rejected_origin_key, {"type": transaction_type}
            )
            assert status == 200
            assert statement["data"] == []


@pytest.mark.parametrize("hour,is_night", [
    ("19:59", False), ("20:00", True), ("00:00", True),
    ("05:59", True), ("06:00", False), ("12:00", False),
])
@pytest.mark.parametrize("operation", ["WITHDRAWAL", "TRANSFER"])
def test_clock_boundaries_are_deterministic_and_rejection_is_atomic(
    api_at_time, make_account, hour, is_night, operation
):
    with api_at_time(hour):
        for amount in (100000, 100001):
            origin = make_account()["response"]["account_key"]
            destination = make_account()["response"]["account_key"] if operation == "TRANSFER" else None
            fee = 100 if operation == "TRANSFER" else 0
            principal_and_fee = amount + fee
            # Mesmo à noite, depósitos acima do limite são aceitos.
            assert RequestGenerator.POST_transaction(
                origin, {"type": "DEPOSIT", "amount": principal_and_fee}
            )[0] == 201
            payload = {"type": operation, "amount": amount}
            if destination:
                payload["destination_account_key"] = destination
            key = str(uuid4())
            status, result = RequestGenerator.POST_transaction(origin, payload, idempotency_key=key)
            rejected = is_night and amount > 100000
            if rejected:
                assert status == 422
                assert result["code"] == "QIT001007"
            else:
                assert status == 201
                if operation == "TRANSFER":
                    assert result["fee_amount"] == fee
            assert RequestGenerator.GET_account(origin)[1]["balance"] == (principal_and_fee if rejected else 0)
            if destination:
                assert RequestGenerator.GET_account(destination)[1]["balance"] == (0 if rejected else amount)
            status, statement = RequestGenerator.GET_transactions(origin)
            assert status == 200
            assert len(statement["data"]) == (1 if rejected else (3 if operation == "TRANSFER" else 2))
            if rejected:
                # Repetir a rejeição não consome saldo/chave nem cria lançamentos.
                assert RequestGenerator.POST_transaction(origin, payload, idempotency_key=key) == (422, result)
                assert RequestGenerator.GET_account(origin)[1]["balance"] == principal_and_fee


@pytest.mark.parametrize("operation", ["WITHDRAWAL", "TRANSFER"])
def test_confirmed_daytime_operation_replays_at_night_without_another_debit(
    api_at_time, make_account, operation
):
    key = str(uuid4())
    with api_at_time("19:59"):
        origin = make_account()["response"]["account_key"]
        destination = make_account()["response"]["account_key"] if operation == "TRANSFER" else None
        assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 300000})[0] == 201
        payload = {"type": operation, "amount": 100001}
        if destination:
            payload["destination_account_key"] = destination
        status, original = RequestGenerator.POST_transaction(origin, payload, idempotency_key=key)
        assert status == 201
        balance = RequestGenerator.GET_account(origin)[1]["balance"]
        entries = RequestGenerator.GET_transactions(origin)[1]["data"]
    with api_at_time("20:00"):
        assert RequestGenerator.POST_transaction(origin, payload, idempotency_key=key) == (201, original)
        assert RequestGenerator.GET_account(origin)[1]["balance"] == balance
        assert RequestGenerator.GET_transactions(origin)[1]["data"] == entries
        status, error = RequestGenerator.POST_transaction(origin, payload)
        assert status == 422
        assert error["code"] == "QIT001007"
        assert RequestGenerator.GET_account(origin)[1]["balance"] == balance
        if destination:
            assert RequestGenerator.GET_account(destination)[1]["balance"] == 100001
