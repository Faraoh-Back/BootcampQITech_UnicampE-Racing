"""Contrato comercial e autorização exercitados pela fronteira HTTP."""

from uuid import uuid4

import pytest

from tests.utils.auth import owner_headers
from tests.utils.request_generator import RequestGenerator


def pricing_proposal(customer_key, **overrides):
    return {
        "customer_key": customer_key,
        "policy_type": "PRICING",
        "policy": {"operation": "TRANSFER", "fixed_fee_cents": 7,
                   "percentage_basis_points": 0, **overrides},
    }


class TestPolicyContract:
    @pytest.mark.parametrize("policy", [
        {},
        {"operation": "UNSUPPORTED", "fixed_fee_cents": 7, "percentage_basis_points": 0},
        {"operation": "TRANSFER", "fixed_fee_cents": -1, "percentage_basis_points": 0},
        {"operation": "TRANSFER", "fixed_fee_cents": 7, "percentage_basis_points": 10001},
        {"operation": "TRANSFER", "fixed_fee_cents": 7.0, "percentage_basis_points": 0},
        {"operation": "TRANSFER", "fixed_fee_cents": 7, "percentage_basis_points": 0, "extra": 1},
        {"operation": "TRANSFER", "fixed_fee_cents": 7, "percentage_basis_points": 0,
         "customer_key": str(uuid4())},
    ])
    def test_rejects_invalid_nested_pricing_before_persisting_draft(self, make_customer, policy):
        customer = make_customer()["response"]["customer_key"]
        status, error = RequestGenerator.POST_policy_change_request(
            {"customer_key": customer, "policy_type": "PRICING", "policy": policy},
            owner_headers(customer),
        )
        assert status == 400
        assert error["code"] == "QIT000001"
        assert set(error) == {"title", "description", "translation", "code"}

    @pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic invalid"])
    def test_requires_valid_jwt_for_proposal(self, make_customer, authorization):
        customer = make_customer()["response"]["customer_key"]
        headers = {} if authorization is None else {"Authorization": authorization}
        status, error = RequestGenerator.POST_policy_change_request(pricing_proposal(customer), headers)
        assert status == 401
        assert error["code"] == "QIT001020"

    def test_proposal_not_found_is_structured(self, make_customer):
        customer = make_customer()["response"]["customer_key"]
        status, error = RequestGenerator.PUT_policy_change_request(
            str(uuid4()), "approve", owner_headers(customer)
        )
        assert status == 404
        assert error["code"] == "QIT001028"

    def test_foreign_owner_and_viewer_cannot_propose(self, make_customer):
        customer = make_customer()["response"]["customer_key"]
        foreign = make_customer()["response"]["customer_key"]
        for headers in (owner_headers(foreign), owner_headers(customer, "VIEWER")):
            status, error = RequestGenerator.POST_policy_change_request(pricing_proposal(customer), headers)
            assert status == 403
            assert error["code"] == "QIT001022"

