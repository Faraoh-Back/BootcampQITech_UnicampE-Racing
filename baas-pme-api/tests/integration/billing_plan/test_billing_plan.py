from datetime import date

import pytest

from tests.utils.mock_server import (
    expect_bankslip_invalid_json,
    expect_bankslip_missing_barcode,
    expect_bankslip_ok,
    expect_bankslip_status,
    expect_bankslip_timeout,
    reset,
    verify_bankslip_external_reference,
    verify_called,
)
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


class TestBillingPlan:
    def test_creates_twelve_monthly_bank_slips_and_exposes_status_events(self, make_account):
        account = make_account()
        assert account["status"] == 201
        expect_bankslip_ok()
        payload = {"base_amount": 15000, "first_due_date": "2027-01-31"}

        status, created = RequestGenerator.POST_billing_plan(account["response"]["account_key"], payload)

        assert status == 201
        assert set(created) == {
            "plan_key", "account_key", "base_amount", "installments_count", "bank_slips", "created_at"
        }
        assert created["account_key"] == account["response"]["account_key"]
        assert created["base_amount"] == 15000
        assert created["installments_count"] == 12
        assert len(created["bank_slips"]) == 12
        assert [slip["installment_number"] for slip in created["bank_slips"]] == list(range(1, 13))
        assert [slip["amount"] for slip in created["bank_slips"]] == [15000] * 12
        assert [slip["due_date"] for slip in created["bank_slips"]] == [
            "2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31", "2027-06-30",
            "2027-07-31", "2027-08-31", "2027-09-30", "2027-10-31", "2027-11-30", "2027-12-31",
        ]
        assert all(slip["status"] == "PENDING" and slip["barcode"].startswith("MOCK-BARCODE-") for slip in created["bank_slips"])
        assert all("id" not in slip for slip in created["bank_slips"])
        verify_called("/bank-slips", 1)
        verify_bankslip_external_reference(f"{created['plan_key']}:batch:1")

        status, found = RequestGenerator.GET_billing_plan(account["response"]["account_key"], created["plan_key"])
        assert status == 200
        assert found["plan_key"] == created["plan_key"]
        assert len(found["bank_slips"]) == 12
        assert all(
            [event["status"] for event in slip["status_events"]] == ["PENDING"]
            for slip in found["bank_slips"]
        )

    def test_rejects_invalid_payload_and_past_due_date(self, make_account):
        account_key = make_account()["response"]["account_key"]
        invalid_payloads = [{}, {"base_amount": 0, "first_due_date": "2027-01-31"}, {"base_amount": 1.5, "first_due_date": "2027-01-31"}, {"base_amount": 100, "first_due_date": "31-01-2027"}, {"base_amount": 100, "first_due_date": "2027-01-31", "extra": True}]

        for payload in invalid_payloads:
            status, response = RequestGenerator.POST_billing_plan(account_key, payload)
            assert status == 400
            assert response["code"] == "QIT000001"

        status, response = RequestGenerator.POST_billing_plan(
            account_key,
            {"base_amount": 100, "first_due_date": "2020-01-01"},
        )
        assert status == 422
        assert response["code"] == "QIT001017"

    def test_hides_plan_of_another_account_and_checks_account_existence(self, make_account):
        first_account = make_account()["response"]["account_key"]
        second_account = make_account()["response"]["account_key"]
        expect_bankslip_ok()
        status, created = RequestGenerator.POST_billing_plan(
            first_account, PayloadGenerator.create_billing_plan_payload(first_due_date="2027-01-31")
        )
        assert status == 201

        status, response = RequestGenerator.GET_billing_plan(second_account, created["plan_key"])
        assert status == 404
        assert response["code"] == "QIT001013"

        status, response = RequestGenerator.POST_billing_plan(
            "00000000-0000-0000-0000-000000000000",
            PayloadGenerator.create_billing_plan_payload(first_due_date="2027-01-31"),
        )
        assert status == 404
        assert response["code"] == "QIT001002"

    @pytest.mark.parametrize(
        "expect_failure",
        [expect_bankslip_timeout, lambda: expect_bankslip_status(500), expect_bankslip_invalid_json, expect_bankslip_missing_barcode],
    )
    def test_external_failure_returns_502_without_persisting_partial_plan(self, make_account, expect_failure):
        account_key = make_account()["response"]["account_key"]
        payload = PayloadGenerator.create_billing_plan_payload(first_due_date="2027-01-31")
        expect_failure()

        status, response = RequestGenerator.POST_billing_plan(account_key, payload)
        assert status == 502
        assert response["code"] == "QIT001009"

        reset()
        expect_bankslip_ok()
        status, created = RequestGenerator.POST_billing_plan(account_key, payload)
        assert status == 201
        assert len(created["bank_slips"]) == 12

    def test_requires_internal_token(self):
        response = ClientRequisition.send(
            "POST",
            "/account/00000000-0000-0000-0000-000000000000/billing-plan",
            payload={"base_amount": 100, "first_due_date": "2027-01-31"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
