from uuid import uuid4

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


class TestTransfer:
    def test_transfer_debits_fee_credits_destination_and_creates_linked_ledger_entries(
        self, make_account
    ):
        origin_key = make_account()["response"]["account_key"]
        destination_key = make_account()["response"]["account_key"]
        status, _ = RequestGenerator.POST_transaction(
            origin_key, {"type": "DEPOSIT", "amount": 1000}
        )
        assert status == 201

        status, transfer = RequestGenerator.POST_transaction(
            origin_key,
            {"type": "TRANSFER", "amount": 500, "destination_account_key": destination_key},
        )

        assert status == 201
        assert set(transfer) == {
            "transaction_key", "type", "amount", "fee_amount", "balance", "created_at"
        }
        assert transfer["type"] == "TRANSFER"
        assert transfer["amount"] == 500
        assert transfer["fee_amount"] == 100
        assert transfer["balance"] == 400

        status, origin = RequestGenerator.GET_account(origin_key)
        assert status == 200
        assert origin["balance"] == 400
        status, destination = RequestGenerator.GET_account(destination_key)
        assert status == 200
        assert destination["balance"] == 500

        status, origin_statement = RequestGenerator.GET_transactions(origin_key, {"limit": 10})
        assert status == 200
        origin_entries = [
            entry for entry in origin_statement["data"] if entry["type"].startswith("TRANSFER")
        ]
        status, destination_statement = RequestGenerator.GET_transactions(
            destination_key, {"limit": 10}
        )
        assert status == 200
        destination_entries = destination_statement["data"]

        assert {(entry["type"], entry["amount"]) for entry in origin_entries} == {
            ("TRANSFER_OUT", -500),
            ("TRANSFER_FEE", -100),
        }
        assert len(destination_entries) == 1
        assert destination_entries[0]["type"] == "TRANSFER_IN"
        assert destination_entries[0]["amount"] == 500
        assert len({entry["operation_key"] for entry in origin_entries + destination_entries}) == 1

        transfer_out = next(entry for entry in origin_entries if entry["type"] == "TRANSFER_OUT")
        transfer_fee = next(entry for entry in origin_entries if entry["type"] == "TRANSFER_FEE")
        transfer_in = destination_entries[0]
        assert transfer_out["counterparty_account_key"] == destination_key
        assert "counterparty_account_key" not in transfer_fee
        assert transfer_in["counterparty_account_key"] == origin_key

    def test_transfer_requires_balance_for_amount_plus_fee_and_is_atomic(self, make_account):
        insufficient_origin_key = make_account()["response"]["account_key"]
        insufficient_destination_key = make_account()["response"]["account_key"]
        RequestGenerator.POST_transaction(
            insufficient_origin_key, {"type": "DEPOSIT", "amount": 500}
        )

        status, error = RequestGenerator.POST_transaction(
            insufficient_origin_key,
            {
                "type": "TRANSFER",
                "amount": 500,
                "destination_account_key": insufficient_destination_key,
            },
        )
        assert status == 422
        assert error["code"] == "QIT001005"
        status, origin = RequestGenerator.GET_account(insufficient_origin_key)
        assert status == 200
        assert origin["balance"] == 500
        status, destination = RequestGenerator.GET_account(insufficient_destination_key)
        assert status == 200
        assert destination["balance"] == 0
        status, entries = RequestGenerator.GET_transactions(
            insufficient_origin_key, {"type": "TRANSFER_OUT"}
        )
        assert status == 200
        assert entries["data"] == []

        exact_origin_key = make_account()["response"]["account_key"]
        exact_destination_key = make_account()["response"]["account_key"]
        RequestGenerator.POST_transaction(exact_origin_key, {"type": "DEPOSIT", "amount": 600})
        status, transfer = RequestGenerator.POST_transaction(
            exact_origin_key,
            {"type": "TRANSFER", "amount": 500, "destination_account_key": exact_destination_key},
        )
        assert status == 201
        assert transfer["balance"] == 0
        status, origin = RequestGenerator.GET_account(exact_origin_key)
        assert status == 200
        assert origin["balance"] == 0
        status, destination = RequestGenerator.GET_account(exact_destination_key)
        assert status == 200
        assert destination["balance"] == 500

    def test_transfer_rejects_invalid_or_unavailable_participants_without_writes(self, make_account):
        origin_key = make_account()["response"]["account_key"]
        destination_key = make_account()["response"]["account_key"]
        RequestGenerator.POST_transaction(origin_key, {"type": "DEPOSIT", "amount": 700})

        status, error = RequestGenerator.POST_transaction(
            origin_key,
            {"type": "TRANSFER", "amount": 100, "destination_account_key": origin_key},
        )
        assert status == 422
        assert error["code"] == "QIT001012"

        status, error = RequestGenerator.POST_transaction(
            origin_key,
            {"type": "TRANSFER", "amount": 100, "destination_account_key": str(uuid4())},
        )
        assert status == 404
        assert error["code"] == "QIT001002"

        status, _ = RequestGenerator.PUT_account_block(destination_key)
        assert status == 200
        status, error = RequestGenerator.POST_transaction(
            origin_key,
            {"type": "TRANSFER", "amount": 100, "destination_account_key": destination_key},
        )
        assert status == 409
        assert error["code"] == "QIT001006"

        status, origin = RequestGenerator.GET_account(origin_key)
        assert status == 200
        assert origin["balance"] == 700
        status, destination = RequestGenerator.GET_account(destination_key)
        assert status == 200
        assert destination["balance"] == 0
        status, entries = RequestGenerator.GET_transactions(origin_key, {"type": "TRANSFER_OUT"})
        assert status == 200
        assert entries["data"] == []

        blocked_origin_key = make_account()["response"]["account_key"]
        approved_destination_key = make_account()["response"]["account_key"]
        RequestGenerator.POST_transaction(blocked_origin_key, {"type": "DEPOSIT", "amount": 700})
        status, _ = RequestGenerator.PUT_account_block(blocked_origin_key)
        assert status == 200
        status, error = RequestGenerator.POST_transaction(
            blocked_origin_key,
            {
                "type": "TRANSFER",
                "amount": 100,
                "destination_account_key": approved_destination_key,
            },
        )
        assert status == 409
        assert error["code"] == "QIT001006"
        status, blocked_origin = RequestGenerator.GET_account(blocked_origin_key)
        assert status == 200
        assert blocked_origin["balance"] == 700
        status, approved_destination = RequestGenerator.GET_account(approved_destination_key)
        assert status == 200
        assert approved_destination["balance"] == 0

    def test_transfer_replays_the_original_response_without_second_debit(self, make_account):
        origin_key = make_account()["response"]["account_key"]
        destination_key = make_account()["response"]["account_key"]
        RequestGenerator.POST_transaction(origin_key, {"type": "DEPOSIT", "amount": 1000})
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": str(uuid4())}
        payload = {"type": "TRANSFER", "amount": 500, "destination_account_key": destination_key}

        first = ClientRequisition.send(
            "POST", f"/account/{origin_key}/transaction", payload=payload, headers=headers
        )
        replay = ClientRequisition.send(
            "POST", f"/account/{origin_key}/transaction", payload=payload, headers=headers
        )

        assert first.response_status == replay.response_status == 201
        assert replay.response_json == first.response_json
        assert replay.response.headers["Idempotent-Replayed"] == "true"
        status, origin = RequestGenerator.GET_account(origin_key)
        assert status == 200
        assert origin["balance"] == 400
        status, destination = RequestGenerator.GET_account(destination_key)
        assert status == 200
        assert destination["balance"] == 500
        status, entries = RequestGenerator.GET_transactions(origin_key, {"type": "TRANSFER_OUT"})
        assert status == 200
        assert len(entries["data"]) == 1
