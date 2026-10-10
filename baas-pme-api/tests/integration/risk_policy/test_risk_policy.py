from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.request_generator import RequestGenerator


def _policy(customer_key, **overrides):
    return {
        "customer_key": customer_key,
        "transfer_enabled": True,
        "billing_plan_enabled": True,
        "credit_advance_enabled": True,
        "max_transfer_amount": 10_000,
        "daily_outgoing_limit": 10_000,
        "max_credit_advance_amount": 1_000_000,
        "max_advance_bank_slips": 50,
        **overrides,
    }


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


class TestRiskPolicy:
    def test_customer_limit_overrides_default_and_daily_usage_is_shared(self, make_customer, make_account):
        constrained_customer = make_customer()["response"]["customer_key"]
        fallback_customer = make_customer()["response"]["customer_key"]
        origin = make_account(constrained_customer)["response"]["account_key"]
        destination = make_account(constrained_customer)["response"]["account_key"]
        fallback_origin = make_account(fallback_customer)["response"]["account_key"]
        fallback_destination = make_account(fallback_customer)["response"]["account_key"]
        status, policy = RequestGenerator.POST_risk_policy(_policy(
            constrained_customer, max_transfer_amount=200, daily_outgoing_limit=300
        ))
        assert status == 201
        assert policy["version"] == 1

        assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 1_000})[0] == 201
        status, transfer = RequestGenerator.POST_transaction(origin, {
            "type": "TRANSFER", "amount": 200, "destination_account_key": destination,
        })
        assert status == 201
        assert transfer["amount"] == 200

        status, error = RequestGenerator.POST_transaction(origin, {
            "type": "TRANSFER", "amount": 150, "destination_account_key": destination,
        })
        assert status == 422
        assert error["code"] == "QIT001027"

        assert RequestGenerator.POST_transaction(fallback_origin, {"type": "DEPOSIT", "amount": 20_000})[0] == 201
        status, _ = RequestGenerator.POST_transaction(fallback_origin, {
            "type": "TRANSFER", "amount": 15_000, "destination_account_key": fallback_destination,
        })
        assert status == 201

    def test_disabled_products_and_advance_limits_return_stable_domain_errors(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(customer_key)["response"]["account_key"]
        status, first_policy = RequestGenerator.POST_risk_policy(_policy(
            customer_key, transfer_enabled=False, billing_plan_enabled=False
        ))
        assert status == 201
        assert first_policy["version"] == 1
        status, error = RequestGenerator.POST_transaction(account_key, {
            "type": "TRANSFER", "amount": 1, "destination_account_key": make_account(customer_key)["response"]["account_key"],
        })
        assert status == 409
        assert error["code"] == "QIT001026"
        status, error = RequestGenerator.POST_billing_plan(account_key, {
            "base_amount": 100, "first_due_date": "2027-01-31",
        })
        assert status == 409
        assert error["code"] == "QIT001026"

        # Nova versão habilita cobrança, mas limita antecipação a um boleto.
        status, second_policy = RequestGenerator.POST_risk_policy(_policy(
            customer_key, max_advance_bank_slips=1
        ))
        assert status == 201
        assert second_policy["version"] == 2
        assert second_policy["policy_key"] != first_policy["policy_key"]
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(account_key, {
            "base_amount": 100, "first_due_date": "2027-01-31",
        })
        assert status == 201
        status, error = RequestGenerator.POST_credit_advance(account_key, {
            "bank_slip_keys": [slip["bank_slip_key"] for slip in plan["bank_slips"][:2]],
        })
        assert status == 422
        assert error["code"] == "QIT001027"

    def test_concurrent_transfers_cannot_cross_the_last_daily_capacity(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        origin_a = make_account(customer_key)["response"]["account_key"]
        origin_b = make_account(customer_key)["response"]["account_key"]
        destination = make_account(customer_key)["response"]["account_key"]
        assert RequestGenerator.POST_risk_policy(_policy(
            customer_key, max_transfer_amount=200, daily_outgoing_limit=200
        ))[0] == 201
        for origin in (origin_a, origin_b):
            assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 500})[0] == 201

        def transfer(origin):
            return RequestGenerator.POST_transaction(origin, {
                "type": "TRANSFER", "amount": 200, "destination_account_key": destination,
            })

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(transfer, (origin_a, origin_b)))
        assert sorted(status for status, _ in results) == [201, 422]
        assert [body["code"] for status, body in results if status == 422] == ["QIT001027"]
