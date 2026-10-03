from tests.utils.request_generator import RequestGenerator


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
