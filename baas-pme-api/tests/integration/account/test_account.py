from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


class TestAccount:
    def test_creates_account_approved_with_auditable_status_history(self, make_customer):
        customer = make_customer()
        assert customer["status"] == 201

        status, created = RequestGenerator.POST_account(
            PayloadGenerator.create_account_payload(customer["response"]["customer_key"])
        )

        assert status == 201
        assert set(created) == {"account_key", "customer_key", "status", "balance", "created_at"}
        assert "id" not in created
        assert created["customer_key"] == customer["response"]["customer_key"]
        assert created["status"] == "APPROVED"
        assert created["balance"] == 0

        status, found = RequestGenerator.GET_account(created["account_key"])
        assert status == 200
        assert found["account_key"] == created["account_key"]
        assert found["customer_key"] == created["customer_key"]
        assert found["status"] == "APPROVED"
        assert found["balance"] == 0
        assert [event["status"] for event in found["status_events"]] == ["PENDING", "APPROVED"]
        assert all("event_datetime" in event for event in found["status_events"])
        assert "id" not in found

    def test_allows_multiple_accounts_for_the_same_customer(self, make_customer):
        customer_key = make_customer()["response"]["customer_key"]
        payload = PayloadGenerator.create_account_payload(customer_key)

        first_status, first = RequestGenerator.POST_account(payload)
        second_status, second = RequestGenerator.POST_account(payload)

        assert first_status == second_status == 201
        assert first["account_key"] != second["account_key"]

    def test_rejects_invalid_payload(self):
        invalid_payloads = [{}, {"customer_key": 1}, {"customer_key": str(uuid4()), "extra": True}]

        for payload in invalid_payloads:
            status, response = RequestGenerator.POST_account(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

        malformed = ClientRequisition.send(
            "POST", "/account", data="{", headers={"INTERNAL-TOKEN": "default_token"}
        )
        assert malformed.response_status == 400
        assert malformed.response_json["code"] == "QIT000001"

    def test_returns_customer_not_found_when_creating_for_unknown_customer(self):
        status, response = RequestGenerator.POST_account(PayloadGenerator.create_account_payload(str(uuid4())))

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_returns_account_not_found_and_requires_token(self):
        status, response = RequestGenerator.GET_account(str(uuid4()))
        assert status == 404
        assert response["code"] == "QIT001002"

        response = ClientRequisition.send("GET", f"/account/{uuid4()}")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
