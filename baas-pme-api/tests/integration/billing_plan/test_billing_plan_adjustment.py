from uuid import uuid4

import pytest

from tests.utils.mock_server import (
    expect_bankslip_ok,
    expect_bankslip_status,
    expect_central_bank_rate,
    expect_central_bank_status,
    reset,
    verify_bankslip_external_reference,
    verify_called,
)
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


@pytest.fixture
def make_plan(make_account):
    def _create(base_amount: int = 15000):
        account_key = make_account()["response"]["account_key"]
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(
            account_key,
            {"base_amount": base_amount, "first_due_date": "2027-01-31"},
        )
        assert status == 201
        return account_key, plan

    return _create


class TestBillingPlanAdjustment:
    @pytest.mark.parametrize(
        ("base_amount", "rate", "expected_amount"),
        [(15000, "4.83", 15725), (15000, "0", 15000), (1000, "0.05", 1001)],
    )
    def test_issues_adjusted_second_batch_with_half_up_rounding(
        self, make_plan, base_amount, rate, expected_amount
    ):
        account_key, plan = make_plan(base_amount)
        reset()
        expect_central_bank_rate("IPCA", rate)
        expect_bankslip_ok(range(13, 25))

        status, adjustment = RequestGenerator.POST_billing_plan_adjustment(
            account_key, plan["plan_key"], {"index_code": "IPCA"}
        )

        assert status == 201
        assert set(adjustment) == {
            "plan_key", "index_code", "accumulated_rate", "adjusted_amount", "bank_slips"
        }
        assert adjustment["plan_key"] == plan["plan_key"]
        assert adjustment["index_code"] == "IPCA"
        assert adjustment["accumulated_rate"] == rate
        assert adjustment["adjusted_amount"] == expected_amount
        assert [slip["installment_number"] for slip in adjustment["bank_slips"]] == list(range(13, 25))
        assert [slip["amount"] for slip in adjustment["bank_slips"]] == [expected_amount] * 12
        assert [slip["due_date"] for slip in adjustment["bank_slips"]] == [
            "2028-01-31", "2028-02-29", "2028-03-31", "2028-04-30", "2028-05-31", "2028-06-30",
            "2028-07-31", "2028-08-31", "2028-09-30", "2028-10-31", "2028-11-30", "2028-12-31",
        ]
        assert all(slip["status"] == "PENDING" for slip in adjustment["bank_slips"])
        verify_called("/bank-slips", 1)
        verify_bankslip_external_reference(f"{plan['plan_key']}:batch:2")

        status, found = RequestGenerator.GET_billing_plan(account_key, plan["plan_key"])
        assert status == 200
        assert len(found["bank_slips"]) == 24
        first_batch, second_batch = found["bank_slips"][:12], found["bank_slips"][12:]
        assert all(slip["batch_number"] == 1 and slip["adjustment_rate"] is None for slip in first_batch)
        assert all(
            slip["batch_number"] == 2 and slip["adjustment_rate"] == rate
            for slip in second_batch
        )
        assert all([event["status"] for event in slip["status_events"]] == ["PENDING"] for slip in second_batch)

        status, error = RequestGenerator.POST_billing_plan_adjustment(
            account_key, plan["plan_key"], {"index_code": "IPCA"}
        )
        assert status == 409
        assert error["code"] == "QIT001014"
        verify_called("/bank-slips", 1)

    def test_rejects_invalid_index_and_hides_plan_from_another_account(self, make_plan, make_account):
        account_key, plan = make_plan()
        for payload in ({}, {"index_code": "SELIC"}, {"index_code": 1}, {"index_code": "IPCA", "x": 1}):
            status, error = RequestGenerator.POST_billing_plan_adjustment(
                account_key, plan["plan_key"], payload
            )
            assert status == 400
            assert error["code"] == "QIT000001"

        other_account_key = make_account()["response"]["account_key"]
        status, error = RequestGenerator.POST_billing_plan_adjustment(
            other_account_key, plan["plan_key"], {"index_code": "IPCA"}
        )
        assert status == 404
        assert error["code"] == "QIT001013"
        status, error = RequestGenerator.POST_billing_plan_adjustment(
            str(uuid4()), plan["plan_key"], {"index_code": "IPCA"}
        )
        assert status == 404
        assert error["code"] == "QIT001002"

    @pytest.mark.parametrize("failure", ["central_bank", "bank_slip"])
    def test_external_failure_leaves_no_second_batch_and_retry_is_safe(self, make_plan, failure):
        account_key, plan = make_plan()
        reset()
        if failure == "central_bank":
            expect_central_bank_status(500)
        else:
            expect_central_bank_rate("IPCA", "4.83")
            expect_bankslip_status(500)

        status, error = RequestGenerator.POST_billing_plan_adjustment(
            account_key, plan["plan_key"], {"index_code": "IPCA"}
        )
        assert status == 502
        assert error["code"] == "QIT001009"
        if failure == "bank_slip":
            verify_bankslip_external_reference(f"{plan['plan_key']}:batch:2")

        status, found = RequestGenerator.GET_billing_plan(account_key, plan["plan_key"])
        assert status == 200
        assert len(found["bank_slips"]) == 12

        # A segunda tentativa recebe a mesma referência do lote 2; como a
        # primeira falhou, somente esta persistirá os boletos.
        reset()
        expect_central_bank_rate("IPCA", "4.83")
        expect_bankslip_ok(range(13, 25))
        status, adjustment = RequestGenerator.POST_billing_plan_adjustment(
            account_key, plan["plan_key"], {"index_code": "IPCA"}
        )
        assert status == 201
        assert adjustment["adjusted_amount"] == 15725
        verify_bankslip_external_reference(f"{plan['plan_key']}:batch:2")
        status, found = RequestGenerator.GET_billing_plan(account_key, plan["plan_key"])
        assert status == 200
        assert len(found["bank_slips"]) == 24

    def test_requires_internal_token(self, make_plan):
        account_key, plan = make_plan()
        response = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/billing-plan/{plan['plan_key']}/adjustment",
            payload={"index_code": "IPCA"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"
