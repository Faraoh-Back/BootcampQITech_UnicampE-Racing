"""Jornada determinística: governa preço, cobra, antecipa, paga e audita."""

from uuid import uuid4

from tests.utils.auth import owner_headers
from tests.utils.mock_server import expect_bankslip_ok, expect_central_bank_rate, reset, verify_called
from tests.utils.request_generator import RequestGenerator


def full_statement(account_key):
    entries = []
    for page in range(100):
        status, statement = RequestGenerator.GET_transactions(account_key, {"page": page, "limit": 2})
        assert status == 200
        assert statement["page"] == page and statement["limit"] == 2
        entries.extend(statement["data"])
        if statement["is_last_page"]:
            assert len({entry["transaction_key"] for entry in entries}) == len(entries)
            return entries
    raise AssertionError("Extrato não terminou em 100 páginas")


def test_pme_full_journey(make_customer, make_account):
    reset()
    try:
        customer = make_customer()
        assert customer["status"] == 201
        customer_key = customer["response"]["customer_key"]
        account = make_account(customer_key)
        assert account["status"] == 201
        origin = account["response"]["account_key"]
        destination = make_account()["response"]["account_key"]
        maker, checker = owner_headers(customer_key), owner_headers(customer_key)

        status, proposal = RequestGenerator.POST_policy_change_request({
            "customer_key": customer_key, "policy_type": "PRICING",
            "policy": {"operation": "TRANSFER", "fixed_fee_cents": 7, "percentage_basis_points": 0},
        }, maker)
        assert status == 201
        assert RequestGenerator.PUT_policy_change_request(proposal["request_key"], "submit", maker)[0] == 200
        status, approved = RequestGenerator.PUT_policy_change_request(proposal["request_key"], "approve", checker)
        assert status == 200 and approved["status"] == "ACTIVE"

        for operation, fee in (("BANK_SLIP_ISSUANCE", 4), ("CREDIT_ADVANCE", 11)):
            assert RequestGenerator.POST_pricing_policy({
                "customer_key": customer_key, "operation": operation,
                "fixed_fee_cents": fee, "percentage_basis_points": 0,
            })[0] == 201
        assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 1000}, headers=maker)[0] == 201

        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(origin, {
            "base_amount": 1000, "first_due_date": "2027-01-31",
        }, maker)
        assert status == 201 and len(plan["bank_slips"]) == 12
        assert plan["issuance_fee_amount"] == 4
        verify_called("/bank-slips", 1)
        reset()
        expect_central_bank_rate("IPCA", "4.83")
        expect_bankslip_ok(range(13, 25))
        status, adjustment = RequestGenerator.POST_billing_plan_adjustment(
            origin, plan["plan_key"], {"index_code": "IPCA"}, maker
        )
        assert status == 201 and adjustment["adjusted_amount"] == 1048
        assert len(adjustment["bank_slips"]) == 12
        verify_called("/bank-slips", 1)
        verify_called("/index/IPCA", 1)

        slips = [plan["bank_slips"][0]["bank_slip_key"], adjustment["bank_slips"][0]["bank_slip_key"]]
        status, quote = RequestGenerator.POST_quote(origin, {
            "operation": "CREDIT_ADVANCE", "bank_slip_keys": slips,
        }, maker)
        assert status == 201 and quote["fee_amount"] == 11
        advance_key = str(uuid4())
        status, advance = RequestGenerator.POST_credit_advance(origin, {"bank_slip_keys": slips}, advance_key, maker)
        assert status == 201 and advance["net_amount"] == 2037
        assert RequestGenerator.POST_credit_advance(origin, {"bank_slip_keys": slips}, advance_key, maker) == (201, advance)
        assert RequestGenerator.POST_credit_advance(origin, {"bank_slip_keys": slips}, headers=maker)[1]["code"] == "QIT001016"

        transfer_key = str(uuid4())
        payload = {"type": "TRANSFER", "amount": 500, "destination_account_key": destination}
        status, transfer = RequestGenerator.POST_transaction(origin, payload, transfer_key, maker)
        assert status == 201 and transfer["fee_amount"] == 7
        assert RequestGenerator.POST_transaction(origin, payload, transfer_key, maker) == (201, transfer)
        assert RequestGenerator.POST_transaction(origin, {"type": "WITHDRAWAL", "amount": 100}, headers=maker)[0] == 201

        for key, expected in ((origin, 2422), (destination, 500)):
            entries = full_statement(key)
            assert sum(entry["amount"] for entry in entries) == expected
            assert RequestGenerator.GET_account(key)[1]["balance"] == expected
        assert len(full_statement(origin)) == 8  # Quatro páginas; inclui todas as tarifas.
        assert RequestGenerator.PUT_account_block(origin, maker)[0] == 200
        assert RequestGenerator.POST_transaction(origin, {"type": "DEPOSIT", "amount": 1}, headers=maker)[1]["code"] == "QIT001006"
        assert RequestGenerator.PUT_account_cancel(origin, maker)[0] == 200
        status, state = RequestGenerator.GET_account(origin, maker)
        assert status == 200 and state["balance"] == 2422
        assert [event["status"] for event in state["status_events"]] == ["PENDING", "APPROVED", "BLOCKED", "CANCELLED"]
        status, audit = RequestGenerator.GET_audit_events()
        assert status == 200
        assert any(event["action"] == "POLICY_CHANGE_APPROVED" and event["resource_key"] == proposal["request_key"] for event in audit["data"])
        assert any(event["action"] == "ACCOUNT_CANCELLED" and event["resource_key"] == origin for event in audit["data"])
    finally:
        reset()
