from uuid import uuid4

from tests.utils.request_generator import RequestGenerator


def _owner(customer_key):
    email = f"owner-{uuid4()}@example.com"
    assert RequestGenerator.POST_user({"customer_key": customer_key, "name": "Owner", "email": email, "password": "secure-pass-123", "role": "OWNER"})[0] == 201
    status, login = RequestGenerator.POST_auth_login({"email": email, "password": "secure-pass-123"})
    assert status == 201
    return {"Authorization": f"Bearer {login['access_token']}"}


class TestMakerChecker:
    def test_other_owner_approves_and_creator_cannot_self_approve(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(customer_key)["response"]["account_key"]
        maker, checker = _owner(customer_key), _owner(customer_key)
        payload = {"customer_key": customer_key, "policy_type": "PRICING", "policy": {
            "operation": "TRANSFER", "fixed_fee_cents": 7, "percentage_basis_points": 0,
        }}
        status, proposal = RequestGenerator.POST_policy_change_request(payload, maker)
        assert status == 201 and proposal["status"] == "DRAFT"
        key = proposal["request_key"]
        assert RequestGenerator.PUT_policy_change_request(key, "submit", maker)[1]["status"] == "PENDING_APPROVAL"
        status, error = RequestGenerator.PUT_policy_change_request(key, "approve", maker)
        assert status == 409 and error["code"] == "QIT001029"

        # Ainda pendente: a tarifa padrão segue vigente, portanto não é selecionada.
        destination = make_account(customer_key)["response"]["account_key"]
        RequestGenerator.POST_transaction(account_key, {"type": "DEPOSIT", "amount": 1_000})
        assert RequestGenerator.POST_transaction(account_key, {"type": "TRANSFER", "amount": 100, "destination_account_key": destination})[1]["fee_amount"] == 100

        status, approved = RequestGenerator.PUT_policy_change_request(key, "approve", checker)
        assert status == 200 and approved["status"] == "ACTIVE" and approved["published_policy_key"]
        RequestGenerator.POST_transaction(account_key, {"type": "DEPOSIT", "amount": 1_000})
        assert RequestGenerator.POST_transaction(account_key, {"type": "TRANSFER", "amount": 100, "destination_account_key": destination})[1]["fee_amount"] == 7
