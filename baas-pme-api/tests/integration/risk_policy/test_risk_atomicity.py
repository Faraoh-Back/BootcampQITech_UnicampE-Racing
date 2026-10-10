from uuid import uuid4

from tests.utils.request_generator import RequestGenerator


def test_failed_transfer_does_not_consume_daily_limit_or_idempotency_key(make_customer, make_account):
    customer = make_customer()["response"]["customer_key"]
    origin = make_account(customer)["response"]["account_key"]
    destination = make_account()["response"]["account_key"]
    assert RequestGenerator.POST_risk_policy({
        "customer_key": customer, "transfer_enabled": True, "billing_plan_enabled": True,
        "credit_advance_enabled": True, "max_transfer_amount": 100,
        "daily_outgoing_limit": 100, "max_credit_advance_amount": 1000,
        "max_advance_bank_slips": 50,
    })[0] == 201
    key = str(uuid4())
    payload = {"type": "TRANSFER", "amount": 100, "destination_account_key": destination}
    status, error = RequestGenerator.POST_transaction(origin, payload, key)
    assert status == 422 and error["code"] == "QIT001005"
    assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 300})[0] == 201
    status, quote = RequestGenerator.POST_quote(origin, {"operation": "TRANSFER", "amount": 100})
    assert status == 201 and quote["daily_outgoing_consumed"] == 0
    status, transfer = RequestGenerator.POST_transaction(origin, payload, key)
    assert status == 201
    assert RequestGenerator.POST_transaction(origin, payload, key) == (201, transfer)
    status, error = RequestGenerator.POST_transaction(origin, payload)
    assert status == 422 and error["code"] == "QIT001027"
    assert RequestGenerator.GET_account(origin)[1]["balance"] == 100
    assert RequestGenerator.GET_account(destination)[1]["balance"] == 100

