from tests.utils.auth import owner_headers
from tests.utils.request_generator import RequestGenerator


def test_quote_requires_membership_when_jwt_is_present(make_customer, make_account):
    customer = make_customer()["response"]["customer_key"]
    foreign = make_customer()["response"]["customer_key"]
    account = make_account(customer)["response"]["account_key"]
    payload = {"operation": "TRANSFER", "amount": 500}
    status, error = RequestGenerator.POST_quote(account, payload, owner_headers(foreign))
    assert status == 403
    assert error["code"] == "QIT001022"
    status, error = RequestGenerator.POST_quote(account, payload, {"Authorization": "Bearer invalid"})
    assert status == 401
    assert error["code"] == "QIT001020"
    status, quote = RequestGenerator.POST_quote(account, payload, owner_headers(customer, "VIEWER"))
    assert status == 201
    assert quote["informative"] is True

