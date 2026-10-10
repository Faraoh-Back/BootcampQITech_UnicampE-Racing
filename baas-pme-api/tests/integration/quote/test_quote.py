from datetime import datetime

import pytest

from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.request_generator import RequestGenerator


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


class TestQuote:
    def test_transfer_quote_uses_customer_price_and_execution_recalculates_current_price(
        self, make_customer, make_account
    ):
        customer_key = make_customer()["response"]["customer_key"]
        origin = make_account(customer_key)["response"]["account_key"]
        destination = make_account(customer_key)["response"]["account_key"]
        status, first_policy = RequestGenerator.POST_pricing_policy({
            "customer_key": customer_key, "operation": "TRANSFER",
            "fixed_fee_cents": 7, "percentage_basis_points": 100,
        })
        assert status == 201

        status, quote = RequestGenerator.POST_quote(origin, {"operation": "TRANSFER", "amount": 500})
        assert status == 201
        assert quote["gross_amount"] == 500
        assert quote["fee_amount"] == 12
        assert quote["net_amount"] == 488
        assert quote["pricing_policy_key"] == first_policy["policy_key"]
        assert quote["informative"] is True
        assert datetime.fromisoformat(quote["expires_at"]) > datetime.now()

        # Uma nova versão de preço torna a cotação antiga apenas informativa;
        # a transferência nunca recebe tarifa do cliente como fonte de verdade.
        status, second_policy = RequestGenerator.POST_pricing_policy({
            "customer_key": customer_key, "operation": "TRANSFER",
            "fixed_fee_cents": 25, "percentage_basis_points": 0,
        })
        assert status == 201
        assert second_policy["version"] == 2
        assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 1_000})[0] == 201
        status, transfer = RequestGenerator.POST_transaction(origin, {
            "type": "TRANSFER", "amount": 500, "destination_account_key": destination,
        })
        assert status == 201
        assert transfer["fee_amount"] == 25

    def test_quotes_are_payload_specific_and_cover_billing_and_advance(self, make_account):
        account_key = make_account()["response"]["account_key"]
        status, first = RequestGenerator.POST_quote(account_key, {"operation": "BILLING_PLAN", "amount": 100})
        assert status == 201
        status, second = RequestGenerator.POST_quote(account_key, {"operation": "BILLING_PLAN", "amount": 200})
        assert status == 201
        assert first["quote_key"] != second["quote_key"]
        assert first["gross_amount"] == 1_200
        assert second["gross_amount"] == 2_400
        assert first["expires_at"] != ""

        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(account_key, {
            "base_amount": 100, "first_due_date": "2027-01-31",
        })
        assert status == 201
        status, advance_quote = RequestGenerator.POST_quote(account_key, {
            "operation": "CREDIT_ADVANCE",
            "bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]],
        })
        assert status == 201
        assert advance_quote["gross_amount"] == 100
        assert advance_quote["fee_amount"] == 3
        assert advance_quote["net_amount"] == 97
