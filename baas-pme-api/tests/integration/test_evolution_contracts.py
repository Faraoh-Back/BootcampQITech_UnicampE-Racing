from uuid import uuid4

import pytest

from tests.utils.request_generator import RequestGenerator


@pytest.mark.parametrize("publish,payload", [
    (RequestGenerator.POST_pricing_policy, {"operation": "TRANSFER", "fixed_fee_cents": 0, "percentage_basis_points": 0}),
    (RequestGenerator.POST_risk_policy, {
        "transfer_enabled": True, "billing_plan_enabled": True, "credit_advance_enabled": True,
        "max_transfer_amount": 1000, "daily_outgoing_limit": 2000,
        "max_credit_advance_amount": 1000, "max_advance_bank_slips": 50,
    }),
])
def test_policy_publication_auth_unknown_customer_and_extra_fields(publish, payload):
    status, error = publish(payload, {"INTERNAL-TOKEN": "invalid"})
    assert status == 403 and error["code"] == "QIT000002"
    status, error = publish({**payload, "customer_key": str(uuid4())})
    assert status == 404 and error["code"] == "QIT001001"
    status, error = publish({**payload, "extra": True})
    assert status == 400 and error["code"] == "QIT000001"
    assert set(error) == {"title", "description", "translation", "code"}


@pytest.mark.parametrize("operation", ["TRANSFER", "BILLING_PLAN"])
@pytest.mark.parametrize("value", [10.0, "10", True, 0, -1])
def test_quote_amount_contract(make_account, operation, value):
    account = make_account()["response"]["account_key"]
    status, error = RequestGenerator.POST_quote(account, {"operation": operation, "amount": value})
    assert status == 400 and error["code"] == "QIT000001"


def test_quote_missing_account_and_unsupported_payload(make_account):
    status, error = RequestGenerator.POST_quote(str(uuid4()), {"operation": "TRANSFER", "amount": 100})
    assert status == 404 and error["code"] == "QIT001002"
    account = make_account()["response"]["account_key"]
    for payload in ({"operation": "TRANSFER"}, {"operation": "INVALID", "amount": 100},
                    {"operation": "TRANSFER", "amount": 100, "fee_amount": 1}):
        status, error = RequestGenerator.POST_quote(account, payload)
        assert status == 400 and error["code"] == "QIT000001"
