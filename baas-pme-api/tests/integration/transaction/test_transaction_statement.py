from uuid import uuid4

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


class TestTransactionStatement:
    def test_empty_statement_and_paginated_ledger_reconstruct_balance(self, make_account):
        empty_account_key = make_account()["response"]["account_key"]
        status, empty_statement = RequestGenerator.GET_transactions(empty_account_key)
        assert status == 200
        assert empty_statement == {"data": [], "page": 0, "limit": 10, "is_last_page": True}

        account_key = make_account()["response"]["account_key"]
        for amount in range(1, 13):
            status, _ = RequestGenerator.POST_transaction(
                account_key, {"type": "DEPOSIT", "amount": amount}
            )
            assert status == 201

        status, first_page = RequestGenerator.GET_transactions(account_key, {"limit": "5", "page": "0"})
        assert status == 200
        assert [entry["amount"] for entry in first_page["data"]] == [12, 11, 10, 9, 8]
        assert first_page["is_last_page"] is False

        status, second_page = RequestGenerator.GET_transactions(account_key, {"limit": "5", "page": "1"})
        assert status == 200
        assert [entry["amount"] for entry in second_page["data"]] == [7, 6, 5, 4, 3]
        assert second_page["is_last_page"] is False

        status, last_page = RequestGenerator.GET_transactions(account_key, {"limit": "5", "page": "2"})
        assert status == 200
        assert [entry["amount"] for entry in last_page["data"]] == [2, 1]
        assert last_page["is_last_page"] is True

        all_entries = first_page["data"] + second_page["data"] + last_page["data"]
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert sum(entry["amount"] for entry in all_entries) == account["balance"] == 78
        assert first_page["data"][0]["balance_after"] == account["balance"]
        assert all("id" not in entry for entry in all_entries)

    def test_filters_by_type_and_exposes_a_transaction_only_to_its_account(self, make_account):
        first_account_key = make_account()["response"]["account_key"]
        second_account_key = make_account()["response"]["account_key"]

        status, deposit = RequestGenerator.POST_transaction(
            first_account_key, {"type": "DEPOSIT", "amount": 100}
        )
        assert status == 201
        status, withdrawal = RequestGenerator.POST_transaction(
            first_account_key, {"type": "WITHDRAWAL", "amount": 25}
        )
        assert status == 201

        status, statement = RequestGenerator.GET_transactions(
            first_account_key, {"type": "WITHDRAWAL"}
        )
        assert status == 200
        assert len(statement["data"]) == 1
        entry = statement["data"][0]
        assert entry["transaction_key"] == withdrawal["transaction_key"]
        assert entry["amount"] == -25
        assert entry["balance_after"] == 75
        assert entry["operation_key"]

        status, found = RequestGenerator.GET_transaction(first_account_key, deposit["transaction_key"])
        assert status == 200
        assert set(found) == {
            "transaction_key", "account_key", "type", "amount", "balance_after", "operation_key", "created_at"
        }
        assert found["account_key"] == first_account_key
        assert found["amount"] == 100

        status, cross_account_error = RequestGenerator.GET_transaction(
            second_account_key, deposit["transaction_key"]
        )
        assert status == 404
        assert cross_account_error["code"] == "QIT001011"

        status, nonexistent_error = RequestGenerator.GET_transaction(second_account_key, str(uuid4()))
        assert status == 404
        assert nonexistent_error == cross_account_error

    def test_rejects_invalid_query_parameters_and_missing_resources(self, make_account):
        account_key = make_account()["response"]["account_key"]
        invalid_params = [
            {"limit": "0"},
            {"limit": "101"},
            {"page": "-1"},
            {"type": "INVALID"},
            {"unknown": "value"},
        ]
        for params in invalid_params:
            status, error = RequestGenerator.GET_transactions(account_key, params)
            assert status == 400
            assert error["code"] == "QIT000001"

        status, error = RequestGenerator.GET_transactions(str(uuid4()))
        assert status == 404
        assert error["code"] == "QIT001002"

        status, error = RequestGenerator.GET_transaction(account_key, str(uuid4()))
        assert status == 404
        assert error["code"] == "QIT001011"

    def test_requires_internal_token(self):
        account_key = str(uuid4())
        response = ClientRequisition.send("GET", f"/account/{account_key}/transactions")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

        response = ClientRequisition.send(
            "GET", f"/account/{account_key}/transaction/{uuid4()}"
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
