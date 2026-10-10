from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from tests.utils.auth import owner_headers
from tests.utils.request_generator import RequestGenerator


def risk_rule(**overrides):
    return {"transfer_enabled": True, "billing_plan_enabled": True,
            "credit_advance_enabled": True, "max_transfer_amount": 1000,
            "daily_outgoing_limit": 2000, "max_credit_advance_amount": 5000,
            "max_advance_bank_slips": 20, **overrides}


@pytest.mark.parametrize("rule", [{}, risk_rule(max_transfer_amount=1.0),
                                 risk_rule(max_advance_bank_slips=51), risk_rule(extra=True)])
def test_nested_risk_contract_is_strict(make_customer, rule):
    customer = make_customer()["response"]["customer_key"]
    status, error = RequestGenerator.POST_policy_change_request({
        "customer_key": customer, "policy_type": "RISK", "policy": rule,
    }, owner_headers(customer))
    assert status == 400
    assert error["code"] == "QIT000001"


@pytest.mark.parametrize("attempt", range(3))
def test_two_checkers_publish_one_risk_version_and_cannot_skip_submission(make_customer, make_account, attempt):
    customer = make_customer()["response"]["customer_key"]
    origin = make_account(customer)["response"]["account_key"]
    destination = make_account()["response"]["account_key"]
    maker = owner_headers(customer)
    checkers = [owner_headers(customer), owner_headers(customer)]
    status, draft = RequestGenerator.POST_policy_change_request({
        "customer_key": customer, "policy_type": "RISK", "policy": risk_rule(transfer_enabled=False),
    }, maker)
    assert status == 201
    key = draft["request_key"]
    for action in ("approve", "submit"):
        status, error = RequestGenerator.PUT_policy_change_request(key, action, checkers[0])
        assert status == 409 and error["code"] == "QIT001029"
    assert RequestGenerator.PUT_policy_change_request(key, "submit", maker)[0] == 200

    barrier = Barrier(2)
    def approve(headers):
        barrier.wait(timeout=10)
        return RequestGenerator.PUT_policy_change_request(key, "approve", headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, checkers))
    assert sorted(status for status, _ in results) == [200, 409]
    approved = next(body for status, body in results if status == 200)
    assert next(body for status, body in results if status == 409)["code"] == "QIT001029"
    assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 1000})[0] == 201
    status, error = RequestGenerator.POST_transaction(origin, {
        "type": "TRANSFER", "amount": 100, "destination_account_key": destination,
    })
    assert status == 409 and error["code"] == "QIT001026"
    # Versionamento observável por uma cotação de outro produto ainda habilitado.
    status, quote = RequestGenerator.POST_quote(origin, {"operation": "BILLING_PLAN", "amount": 100})
    assert status == 201
    assert quote["risk_policy_key"] == approved["published_policy_key"]
    assert quote["risk_policy_version"] == 1
    status, audit = RequestGenerator.GET_audit_events()
    assert status == 200
    events = [event for event in audit["data"] if event["resource_key"] == key]
    assert [event["action"] for event in events] == ["POLICY_CHANGE_DRAFTED", "POLICY_CHANGE_SUBMITTED", "POLICY_CHANGE_APPROVED"]
    assert all(event["actor_type"] == "USER" for event in events)
    assert events[0]["actor_key"] != events[-1]["actor_key"]

