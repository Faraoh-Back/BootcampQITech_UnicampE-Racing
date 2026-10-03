from uuid import uuid4

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


class TestTransaction:
    def test_deposit_and_withdrawal_update_balance_and_return_ledger_entry(self, make_account):
        account_key = make_account()["response"]["account_key"]

        status, deposited = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 50000}
        )
        assert status == 201
        assert set(deposited) == {
            "transaction_key", "type", "amount", "balance", "created_at"
        }
        assert deposited["type"] == "DEPOSIT"
        assert deposited["amount"] == 50000
        assert deposited["balance"] == 50000

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 50000

        status, withdrawn = RequestGenerator.POST_transaction(
            account_key, {"type": "WITHDRAWAL", "amount": 12345}
        )
        assert status == 201
        assert withdrawn["type"] == "WITHDRAWAL"
        assert withdrawn["amount"] == 12345
        assert withdrawn["balance"] == 37655
        assert withdrawn["transaction_key"] != deposited["transaction_key"]

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 37655

    def test_refuses_withdrawal_without_balance_and_preserves_cached_balance(self, make_account):
        account_key = make_account()["response"]["account_key"]

        status, error = RequestGenerator.POST_transaction(
            account_key, {"type": "WITHDRAWAL", "amount": 1}
        )
        assert status == 422
        assert error["code"] == "QIT001005"

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 0

        status, _ = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 201
        status, error = RequestGenerator.POST_transaction(
            account_key, {"type": "WITHDRAWAL", "amount": 101}
        )
        assert status == 422
        assert error["code"] == "QIT001005"

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 100

    def test_rejects_invalid_payloads_and_unknown_account(self, make_account):
        account_key = make_account()["response"]["account_key"]
        invalid_payloads = [
            {},
            {"type": "DEPOSIT", "amount": 0},
            {"type": "DEPOSIT", "amount": -1},
            {"type": "DEPOSIT", "amount": 10.5},
            {"type": "DEPOSIT", "amount": 10.0},
            {"type": "DEPOSIT", "amount": "10"},
            {"type": "INVALID", "amount": 10},
            {"type": "DEPOSIT", "amount": 10, "destination_account_key": str(uuid4())},
            {"type": "WITHDRAWAL", "amount": 10, "destination_account_key": str(uuid4())},
            {"type": "TRANSFER", "amount": 10},
        ]
        for payload in invalid_payloads:
            status, error = RequestGenerator.POST_transaction(account_key, payload)
            assert status == 400
            assert error["code"] == "QIT000001"

        status, error = RequestGenerator.POST_transaction(
            str(uuid4()), {"type": "DEPOSIT", "amount": 10}
        )
        assert status == 404
        assert error["code"] == "QIT001002"

    def test_refuses_financial_operations_for_blocked_or_cancelled_accounts(self, make_account):
        blocked_account_key = make_account()["response"]["account_key"]
        cancelled_account_key = make_account()["response"]["account_key"]

        status, _ = RequestGenerator.PUT_account_block(blocked_account_key)
        assert status == 200
        status, error = RequestGenerator.POST_transaction(
            blocked_account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 409
        assert error["code"] == "QIT001006"

        status, _ = RequestGenerator.PUT_account_cancel(cancelled_account_key)
        assert status == 200
        status, error = RequestGenerator.POST_transaction(
            cancelled_account_key, {"type": "WITHDRAWAL", "amount": 1}
        )
        assert status == 409
        assert error["code"] == "QIT001006"

        for account_key in (blocked_account_key, cancelled_account_key):
            status, account = RequestGenerator.GET_account(account_key)
            assert status == 200
            assert account["balance"] == 0

    def test_requires_internal_token(self):
        response = ClientRequisition.send(
            "POST",
            f"/account/{uuid4()}/transaction",
            payload={"type": "DEPOSIT", "amount": 10},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_requires_idempotency_key_after_internal_authentication(self, make_account):
        account_key = make_account()["response"]["account_key"]

        response = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/transaction",
            payload={"type": "DEPOSIT", "amount": 10},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        assert response.response_status == 400
        assert response.response_json["code"] == "QIT001018"

    def test_replays_same_response_once_for_same_key_and_canonical_payload(self, make_account):
        account_key = make_account()["response"]["account_key"]
        idempotency_key = str(uuid4())
        headers = {
            "INTERNAL-TOKEN": INTERNAL_TOKEN,
            "Idempotency-Key": idempotency_key,
        }

        first = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/transaction",
            payload={"type": "DEPOSIT", "amount": 100},
            headers=headers,
        )
        replay = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/transaction",
            payload={"amount": 100, "type": "DEPOSIT"},
            headers=headers,
        )

        assert first.response_status == replay.response_status == 201
        assert replay.response_json == first.response_json
        assert replay.response.headers["Idempotent-Replayed"] == "true"

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 100

    def test_rejects_changed_payload_but_allows_same_payload_with_a_new_key(self, make_account):
        account_key = make_account()["response"]["account_key"]
        first_key = str(uuid4())
        payload = {"type": "DEPOSIT", "amount": 100}

        status, _ = RequestGenerator.POST_transaction(account_key, payload, idempotency_key=first_key)
        assert status == 201
        status, error = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 101}, idempotency_key=first_key
        )
        assert status == 409
        assert error["code"] == "QIT001008"

        status, _ = RequestGenerator.POST_transaction(
            account_key, payload, idempotency_key=str(uuid4())
        )
        assert status == 201
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 200

    def test_does_not_store_failed_operation_and_scopes_key_per_account(self, make_account):
        first_account_key = make_account()["response"]["account_key"]
        second_account_key = make_account()["response"]["account_key"]
        failed_key = str(uuid4())

        status, error = RequestGenerator.POST_transaction(
            first_account_key,
            {"type": "WITHDRAWAL", "amount": 100},
            idempotency_key=failed_key,
        )
        assert status == 422
        assert error["code"] == "QIT001005"

        status, _ = RequestGenerator.POST_transaction(
            first_account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 201
        status, retried = RequestGenerator.POST_transaction(
            first_account_key,
            {"type": "WITHDRAWAL", "amount": 100},
            idempotency_key=failed_key,
        )
        assert status == 201
        assert retried["balance"] == 0

        shared_key = str(uuid4())
        status, _ = RequestGenerator.POST_transaction(
            first_account_key, {"type": "DEPOSIT", "amount": 1}, idempotency_key=shared_key
        )
        assert status == 201
        status, second = RequestGenerator.POST_transaction(
            second_account_key, {"type": "DEPOSIT", "amount": 1}, idempotency_key=shared_key
        )
        assert status == 201
        assert second["balance"] == 1
