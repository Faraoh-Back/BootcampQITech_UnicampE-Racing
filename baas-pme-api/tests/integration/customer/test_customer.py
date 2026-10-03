from uuid import uuid4

from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


class TestCustomer:
    def test_create_and_get_customer(self):
        payload = PayloadGenerator.create_customer_payload()

        status, created = RequestGenerator.POST_customer(payload)

        assert status == 201
        assert set(created) == {"customer_key"}
        assert "id" not in created

        status, found = RequestGenerator.GET_customer(created["customer_key"])
        assert status == 200
        assert found["customer_key"] == created["customer_key"]
        assert found["name"] == payload["name"]
        assert found["email"] == payload["email"]
        assert found["document_number"] == payload["document_number"]

    def test_rejects_invalid_body(self):
        valid = PayloadGenerator.create_customer_payload()
        invalid_payloads = [
            {},
            {"name": valid["name"], "email": valid["email"]},
            {**valid, "unexpected": True},
            {**valid, "name": 123},
            {**valid, "document_number": "12345678901"},
        ]

        for payload in invalid_payloads:
            status, response = RequestGenerator.POST_customer(payload)
            assert status == 400
            assert response["code"] == "QIT000001"

        malformed = ClientRequisition.send(
            "POST", "/customer", data="{", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        )
        assert malformed.response_status == 400
        assert malformed.response_json["code"] == "QIT000001"

        empty_body = ClientRequisition.send(
            "POST", "/customer", data="", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        )
        assert empty_body.response_status == 400
        assert empty_body.response_json["code"] == "QIT000001"

    def test_rejects_invalid_cpf_and_cnpj(self):
        for document_number in (RandomGenerator.generate_invalid_cpf(), RandomGenerator.generate_invalid_cnpj()):
            status, response = RequestGenerator.POST_customer(
                PayloadGenerator.create_customer_payload(document_number=document_number)
            )
            assert status == 422
            assert response["code"] == "QIT001010"

    def test_rejects_duplicate_document_and_email(self):
        payload = PayloadGenerator.create_customer_payload()
        status, _ = RequestGenerator.POST_customer(payload)
        assert status == 201

        status, response = RequestGenerator.POST_customer({**payload, "email": f"other.{uuid4().hex}@example.com"})
        assert status == 409
        assert response["code"] == "QIT001003"

        status, response = RequestGenerator.POST_customer(
            {**payload, "document_number": RandomGenerator.generate_cnpj()}
        )
        assert status == 409
        assert response["code"] == "QIT001004"

    def test_returns_not_found_and_requires_internal_token(self):
        status, response = RequestGenerator.GET_customer(str(uuid4()))
        assert status == 404
        assert response["code"] == "QIT001001"

        response = ClientRequisition.send("POST", "/customer", payload=PayloadGenerator.create_customer_payload())
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
