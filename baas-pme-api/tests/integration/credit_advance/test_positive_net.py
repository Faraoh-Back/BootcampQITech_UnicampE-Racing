"""Regra econômica da antecipação, exclusivamente por HTTP (sem importar src)."""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from tests.utils.mock_server import expect_bankslip_ok, reset
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


INVALID_PRICES = [
    pytest.param(10000, 10000, 0, id="fixed-equal"),
    pytest.param(10000, 12000, 0, id="fixed-greater"),
    pytest.param(10000, 0, 10000, id="percentage-equal"),
    pytest.param(10000, 100, 10000, id="percentage-plus-fixed-greater"),
    pytest.param(10000, 100, 9900, id="combined-equal"),
    pytest.param(10000, 200, 9900, id="combined-greater"),
    pytest.param(1, 0, 5000, id="half-up-to-zero-net"),
    pytest.param(1, 1, 5000, id="half-up-to-negative-net"),
    pytest.param(10000, 9223372036854775807, 1, id="computed-fee-exceeds-bigint"),
]


@pytest.fixture(autouse=True)
def reset_mockserver():
    reset()
    yield
    reset()


@pytest.fixture
def receivables(make_account):
    def create(base_amount=10000, initial_balance=0):
        account = make_account()
        assert account["status"] == 201
        account_key = account["response"]["account_key"]
        if initial_balance:
            assert RequestGenerator.POST_transaction(
                account_key, {"type": "DEPOSIT", "amount": initial_balance}
            )[0] == 201
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(account_key, {
            "base_amount": base_amount,
            "first_due_date": (date.today() + timedelta(days=90)).isoformat(),
        })
        assert status == 201
        return account["customer_key"], account_key, plan
    return create


def publish_price(customer_key, fixed, basis_points):
    status, policy = RequestGenerator.POST_pricing_policy({
        "customer_key": customer_key, "operation": "CREDIT_ADVANCE",
        "fixed_fee_cents": fixed, "percentage_basis_points": basis_points,
    })
    assert status == 201
    return policy


def send_advance(account_key, payload, key):
    return ClientRequisition.send("POST", f"/account/{account_key}/credit-advance",
        payload=payload,
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": key})


def financial_state(account_key, plan_key):
    result = []
    for status, body in (
        RequestGenerator.GET_account(account_key),
        RequestGenerator.GET_transactions(account_key, {"limit": 100}),
        RequestGenerator.GET_billing_plan(account_key, plan_key),
        RequestGenerator.GET_audit_checkpoint(),
    ):
        assert status == 200
        result.append(body)
    return result


def retry_counters():
    response = ClientRequisition.send("GET", "/metrics",
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
    assert response.response_status == 200
    return sorted(line for line in response.response_content.decode().splitlines()
        if line.startswith("baas_database_transient_retries_total{"))


def assert_non_positive_error(response):
    assert response.response_status == 422
    assert set(response.response_json) == {"title", "description", "translation", "code"}
    assert response.response_json["code"] == "QIT001030"
    assert response.response_json["title"] == "Non-positive credit advance"
    assert response.response.headers.get("X-Request-ID")
    assert "Idempotent-Replayed" not in response.response.headers


@pytest.mark.parametrize("base_amount,fixed,basis_points", INVALID_PRICES)
@pytest.mark.parametrize("initial_balance", [0, 50000], ids=["no-prior-balance", "funded"])
def test_rejects_non_positive_advance_without_effects_or_business_retry(
    receivables, base_amount, fixed, basis_points, initial_balance
):
    customer, account, plan = receivables(base_amount, initial_balance)
    publish_price(customer, fixed, basis_points)
    payload = {"bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
    key = str(uuid4())
    before = financial_state(account, plan["plan_key"])
    retries = retry_counters()

    # Duas recusas da mesma intenção não confirmam reserva nem consomem lastro.
    for _ in range(2):
        assert_non_positive_error(send_advance(account, payload, key))
        assert financial_state(account, plan["plan_key"]) == before
    assert retry_counters() == retries

    # Política corrigida permite concluir a mesma chave/corpo, pois não houve commit.
    publish_price(customer, 0, 0)
    created = send_advance(account, payload, key)
    assert created.response_status == 201
    assert created.response_json["net_amount"] == base_amount
    assert created.response_json["balance"] == initial_balance + base_amount
    replay = send_advance(account, payload, key)
    assert replay.response_status == 201
    assert replay.response_json == created.response_json
    assert replay.response.headers["Idempotent-Replayed"] == "true"


@pytest.mark.parametrize("base_amount,fixed,basis_points", INVALID_PRICES)
def test_quote_rejects_non_positive_advance_without_persisted_quote_or_lastro(
    receivables, base_amount, fixed, basis_points
):
    customer, account, plan = receivables(base_amount, 50000)
    publish_price(customer, fixed, basis_points)
    payload = {"operation": "CREDIT_ADVANCE",
        "bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
    before = financial_state(account, plan["plan_key"])
    response = ClientRequisition.send("POST", f"/account/{account}/quote",
        payload=payload, headers={"INTERNAL-TOKEN": INTERNAL_TOKEN})
    assert_non_positive_error(response)
    assert financial_state(account, plan["plan_key"]) == before

    publish_price(customer, 0, 0)
    status, quote = RequestGenerator.POST_quote(account, payload)
    assert status == 201
    assert quote["net_amount"] == base_amount
    assert RequestGenerator.POST_credit_advance(account,
        {"bank_slip_keys": payload["bank_slip_keys"]})[0] == 201


@pytest.mark.parametrize("base_amount,fixed,basis_points,count,fee,net", [
    pytest.param(10000, 0, 0, 1, 0, 10000, id="free"),
    pytest.param(10000, 100, 300, 1, 400, 9600, id="combined"),
    pytest.param(10000, 9999, 0, 1, 9999, 1, id="one-cent-fixed"),
    pytest.param(3, 0, 5000, 1, 2, 1, id="one-cent-half-up"),
    pytest.param(1, 0, 4999, 1, 0, 1, id="one-cent-rounded-down"),
    pytest.param(10000, 12000, 0, 2, 12000, 8000, id="sum-of-two-slips"),
    pytest.param(100000, 12000, 0, 1, 12000, 88000, id="high-fee-valid-for-larger-gross"),
])
def test_quote_and_execution_accept_positive_net_and_reconcile_ledger(
    receivables, base_amount, fixed, basis_points, count, fee, net
):
    customer, account, plan = receivables(base_amount)
    policy = publish_price(customer, fixed, basis_points)
    payload = {"bank_slip_keys": [slip["bank_slip_key"] for slip in plan["bank_slips"][:count]]}
    status, quote = RequestGenerator.POST_quote(account, {"operation": "CREDIT_ADVANCE", **payload})
    assert status == 201
    assert (quote["gross_amount"], quote["fee_amount"], quote["net_amount"]) == (base_amount * count, fee, net)
    assert quote["pricing_policy_key"] == policy["policy_key"]
    assert RequestGenerator.GET_account(account)[1]["balance"] == 0

    created = send_advance(account, payload, str(uuid4()))
    assert created.response_status == 201
    assert (created.response_json["gross_amount"], created.response_json["fee_amount"],
        created.response_json["net_amount"], created.response_json["balance"]) == (base_amount * count, fee, net, net)
    for field in ("gross_amount", "fee_amount", "net_amount", "balance"):
        assert type(created.response_json[field]) is int
    status, statement = RequestGenerator.GET_transactions(account, {"limit": 100})
    assert status == 200
    assert sum(entry["amount"] for entry in statement["data"]) == net
    assert len(statement["data"]) == (2 if fee else 1)
    found = RequestGenerator.GET_billing_plan(account, plan["plan_key"])[1]
    linked = [slip for slip in found["bank_slips"] if "credit_advance_key" in slip]
    assert len(linked) == count
    assert {slip["credit_advance_key"] for slip in linked} == {created.response_json["credit_advance_key"]}


def test_success_replay_keeps_original_price_after_new_invalid_policy(receivables):
    customer, account, plan = receivables()
    publish_price(customer, 300, 0)
    payload = {"bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
    key = str(uuid4())
    created = send_advance(account, payload, key)
    assert created.response_status == 201
    publish_price(customer, 12000, 0)
    before = financial_state(account, plan["plan_key"])
    replay = send_advance(account, payload, key)
    assert replay.response_status == 201
    assert replay.response_json == created.response_json
    assert replay.response.headers["Idempotent-Replayed"] == "true"
    assert financial_state(account, plan["plan_key"]) == before
    other = {"bank_slip_keys": [plan["bank_slips"][1]["bank_slip_key"]]}
    changed = send_advance(account, other, key)
    assert changed.response_status == 409
    assert changed.response_json["code"] == "QIT001008"
    assert_non_positive_error(send_advance(account, other, str(uuid4())))


def test_execution_recalculates_positive_quote_after_policy_changes(receivables):
    customer, account, plan = receivables()
    publish_price(customer, 300, 0)
    payload = {"bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
    status, quote = RequestGenerator.POST_quote(account, {"operation": "CREDIT_ADVANCE", **payload})
    assert status == 201
    assert quote["net_amount"] == 9700
    publish_price(customer, 10000, 0)
    before = financial_state(account, plan["plan_key"])
    assert_non_positive_error(send_advance(account, payload, str(uuid4())))
    assert financial_state(account, plan["plan_key"]) == before
