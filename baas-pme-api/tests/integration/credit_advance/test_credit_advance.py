from uuid import uuid4

import pytest

from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


@pytest.fixture
def make_plan(make_account):
    def _create(base_amount: int = 10000):
        account_key = make_account()["response"]["account_key"]
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(
            account_key,
            {"base_amount": base_amount, "first_due_date": "2027-01-31"},
        )
        assert status == 201
        return account_key, plan

    return _create


class TestCreditAdvance:
    @pytest.mark.parametrize(
        ("base_amount", "expected_fee", "expected_net"),
        [(10000, 300, 9700), (1050, 32, 1018)],
    )
    def test_advances_pending_bank_slip_and_writes_auditable_ledger(
        self, make_plan, base_amount, expected_fee, expected_net
    ):
        account_key, plan = make_plan(base_amount)
        bank_slip_key = plan["bank_slips"][0]["bank_slip_key"]

        status, advanced = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [bank_slip_key]}
        )

        assert status == 201
        assert set(advanced) == {
            "credit_advance_key", "gross_amount", "fee_amount", "net_amount", "balance",
            "bank_slip_keys", "created_at",
        }
        assert advanced["gross_amount"] == base_amount
        assert advanced["fee_amount"] == expected_fee
        assert advanced["net_amount"] == expected_net
        assert advanced["balance"] == expected_net
        assert advanced["bank_slip_keys"] == [bank_slip_key]

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == expected_net
        status, credit_entries = RequestGenerator.GET_transactions(
            account_key, {"type": "ADVANCE_CREDIT"}
        )
        assert status == 200
        status, fee_entries = RequestGenerator.GET_transactions(account_key, {"type": "ADVANCE_FEE"})
        assert status == 200
        assert len(credit_entries["data"]) == len(fee_entries["data"]) == 1
        assert credit_entries["data"][0]["amount"] == base_amount
        assert fee_entries["data"][0]["amount"] == -expected_fee
        assert credit_entries["data"][0]["operation_key"] == fee_entries["data"][0]["operation_key"]

        status, found_plan = RequestGenerator.GET_billing_plan(account_key, plan["plan_key"])
        assert status == 200
        advanced_slip = next(
            slip for slip in found_plan["bank_slips"] if slip["bank_slip_key"] == bank_slip_key
        )
        assert advanced_slip["status"] == "PENDING"
        assert advanced_slip["credit_advance_key"] == advanced["credit_advance_key"]

    def test_rejects_already_advanced_slip_and_hides_foreign_or_missing_slips(self, make_plan):
        account_key, plan = make_plan()
        bank_slip_key = plan["bank_slips"][0]["bank_slip_key"]
        status, _ = RequestGenerator.POST_credit_advance(account_key, {"bank_slip_keys": [bank_slip_key]})
        assert status == 201

        status, error = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [bank_slip_key]}
        )
        assert status == 409
        assert error["code"] == "QIT001016"

        other_account_key, other_plan = make_plan()
        foreign_key = other_plan["bank_slips"][0]["bank_slip_key"]
        status, foreign_error = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [foreign_key]}
        )
        status_missing, missing_error = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [str(uuid4())]}
        )
        assert status == status_missing == 404
        assert foreign_error == missing_error
        assert foreign_error["code"] == "QIT001015"
        status, other_account = RequestGenerator.GET_account(other_account_key)
        assert status == 200
        assert other_account["balance"] == 0

    def test_rejects_invalid_lists_and_preserves_all_slips_when_one_is_missing(self, make_plan):
        account_key, plan = make_plan()
        valid_key = plan["bank_slips"][0]["bank_slip_key"]
        invalid_payloads = [
            {},
            {"bank_slip_keys": []},
            {"bank_slip_keys": [valid_key, valid_key]},
            {"bank_slip_keys": [str(uuid4()) for _ in range(51)]},
            {"bank_slip_keys": [1]},
            {"bank_slip_keys": [valid_key], "extra": True},
        ]
        for payload in invalid_payloads:
            status, error = RequestGenerator.POST_credit_advance(account_key, payload)
            assert status == 400
            assert error["code"] == "QIT000001"

        status, error = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [valid_key, str(uuid4())]}
        )
        assert status == 404
        assert error["code"] == "QIT001015"
        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 0
        status, found_plan = RequestGenerator.GET_billing_plan(account_key, plan["plan_key"])
        assert status == 200
        valid_slip = next(slip for slip in found_plan["bank_slips"] if slip["bank_slip_key"] == valid_key)
        assert "credit_advance_key" not in valid_slip

        status, advanced = RequestGenerator.POST_credit_advance(
            account_key, {"bank_slip_keys": [valid_key]}
        )
        assert status == 201
        assert advanced["gross_amount"] == 10000

    def test_requires_idempotency_replays_response_and_refuses_blocked_account(self, make_plan):
        account_key, plan = make_plan()
        first_key, second_key = (
            plan["bank_slips"][0]["bank_slip_key"],
            plan["bank_slips"][1]["bank_slip_key"],
        )
        headers = {"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": str(uuid4())}
        payload = {"bank_slip_keys": [first_key]}
        first = ClientRequisition.send(
            "POST", f"/account/{account_key}/credit-advance", payload=payload, headers=headers
        )
        replay = ClientRequisition.send(
            "POST", f"/account/{account_key}/credit-advance", payload=payload, headers=headers
        )
        assert first.response_status == replay.response_status == 201
        assert first.response_json == replay.response_json
        assert replay.response.headers["Idempotent-Replayed"] == "true"

        changed = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/credit-advance",
            payload={"bank_slip_keys": [second_key]},
            headers=headers,
        )
        assert changed.response_status == 409
        assert changed.response_json["code"] == "QIT001008"

        status, account = RequestGenerator.GET_account(account_key)
        assert status == 200
        assert account["balance"] == 9700

        blocked_account_key, blocked_plan = make_plan()
        blocked_slip_key = blocked_plan["bank_slips"][0]["bank_slip_key"]
        status, _ = RequestGenerator.PUT_account_block(blocked_account_key)
        assert status == 200
        status, error = RequestGenerator.POST_credit_advance(
            blocked_account_key, {"bank_slip_keys": [blocked_slip_key]}
        )
        assert status == 409
        assert error["code"] == "QIT001006"

        response = ClientRequisition.send(
            "POST",
            f"/account/{blocked_account_key}/credit-advance",
            payload={"bank_slip_keys": [blocked_slip_key]},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT001018"
