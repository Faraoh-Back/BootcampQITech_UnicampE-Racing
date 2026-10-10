import pytest

from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.request_generator import RequestGenerator


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


class TestReceivablesProductFlow:
    """Jornada HTTP que separa cobrança da PME de antecipação de recebíveis."""

    def test_pme_issues_own_receivables_then_advances_them_once(self, make_account):
        issuer_key = make_account()["response"]["account_key"]
        other_pme_key = make_account()["response"]["account_key"]

        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(issuer_key, {
            "base_amount": 15_000,
            "first_due_date": "2027-01-31",
        })
        assert status == 201
        assert plan["installments_count"] == 12
        receivable_key = plan["bank_slips"][0]["bank_slip_key"]

        # O recebível não vaza nem pode lastrear liquidez de outra PME.
        status, error = RequestGenerator.POST_credit_advance(other_pme_key, {
            "bank_slip_keys": [receivable_key],
        })
        assert status == 404
        assert error["code"] == "QIT001015"

        status, advance = RequestGenerator.POST_credit_advance(issuer_key, {
            "bank_slip_keys": [receivable_key],
        })
        assert status == 201
        assert advance["gross_amount"] == 15_000
        assert advance["fee_amount"] == 450
        assert advance["net_amount"] == 14_550
        assert advance["bank_slip_keys"] == [receivable_key]

        status, statement = RequestGenerator.GET_transactions(issuer_key, {"limit": 20})
        assert status == 200
        entries = [entry for entry in statement["data"] if entry["type"].startswith("ADVANCE_")]
        assert {(entry["type"], entry["amount"]) for entry in entries} == {
            ("ADVANCE_CREDIT", 15_000),
            ("ADVANCE_FEE", -450),
        }

        # A mesma duplicata não pode gerar uma segunda liquidez.
        status, error = RequestGenerator.POST_credit_advance(issuer_key, {
            "bank_slip_keys": [receivable_key],
        })
        assert status == 409
        assert error["code"] == "QIT001016"
