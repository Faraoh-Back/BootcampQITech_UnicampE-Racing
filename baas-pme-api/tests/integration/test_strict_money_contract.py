"""Nenhuma coerção de número monetário deve ocorrer na fronteira JSON."""

import pytest

from tests.utils.mock_server import reset, verify_called
from tests.utils.request_generator import RequestGenerator


@pytest.mark.parametrize("value", [10.0, "10", True, 0, -1])
def test_billing_amount_rejects_non_integer_or_non_positive_before_connector(make_account, value):
    account = make_account()["response"]["account_key"]
    reset()
    try:
        status, error = RequestGenerator.POST_billing_plan(
            account, {"base_amount": value, "first_due_date": "2027-01-31"}
        )
        assert status == 400
        assert error["code"] == "QIT000001"
        verify_called("/bank-slips", 0)
        assert RequestGenerator.GET_account(account)[1]["balance"] == 0
        assert RequestGenerator.GET_transactions(account)[1]["data"] == []
    finally:
        reset()

