import hashlib
import json
from os import environ

import psycopg2
import pytest

from tests.utils.request_generator import RequestGenerator
from tests.utils.mock_server import expect_bankslip_ok, reset


GENESIS_HASH = "0" * 64


def _event_hash(event: dict) -> str:
    payload = {
        "actor_key": event["actor_key"],
        "actor_type": event["actor_type"],
        "action": event["action"],
        "current_summary": event["current_summary"],
        "event_datetime": event["event_datetime"],
        "origin": event["origin"],
        "previous_hash": event["previous_hash"],
        "previous_summary": event["previous_summary"],
        "request_id": event["request_id"],
        "resource_key": event["resource_key"],
        "resource_type": event["resource_type"],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _database_connection():
    url = environ.get(
        "DATABASE_URL", "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"
    )
    return psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1))


class TestVerifiableAudit:
    @pytest.fixture(autouse=True)
    def reset_mockserver(self):
        reset()
        yield
        reset()

    def test_records_domain_events_and_recalculates_the_full_hash_chain(
        self, make_customer, make_account
    ):
        customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(customer_key)["response"]["account_key"]
        status, transaction = RequestGenerator.POST_transaction(
            account_key, {"type": "DEPOSIT", "amount": 250}
        )
        assert status == 201
        status, _ = RequestGenerator.PUT_account_block(account_key)
        assert status == 200
        status, _ = RequestGenerator.PUT_account_cancel(account_key)
        assert status == 200

        status, exported = RequestGenerator.GET_audit_events()
        assert status == 200
        events = exported["data"]
        assert events == sorted(events, key=lambda event: event["audit_event_id"])

        previous_hash = GENESIS_HASH
        for event in events:
            assert event["previous_hash"] == previous_hash
            assert event["event_hash"] == _event_hash(event)
            assert event["request_id"]
            assert event["origin"]
            previous_hash = event["event_hash"]

        forged = {**events[-1], "action": "FORGED"}
        assert _event_hash(forged) != events[-1]["event_hash"]

        actions = {
            (event["action"], event["resource_key"])
            for event in events
        }
        assert ("CUSTOMER_CREATED", customer_key) in actions
        assert ("ACCOUNT_CREATED", account_key) in actions
        assert ("DEPOSIT_CREATED", transaction["transaction_key"]) in actions
        assert ("ACCOUNT_BLOCKED", account_key) in actions
        assert ("ACCOUNT_CANCELLED", account_key) in actions
        assert exported["checkpoint"]["event_hash"] == previous_hash

        status, checkpoint = RequestGenerator.GET_audit_checkpoint()
        assert status == 200
        assert checkpoint == exported["checkpoint"]

    def test_database_rejects_update_and_delete_of_audit_events(self, make_customer):
        make_customer()
        status, exported = RequestGenerator.GET_audit_events()
        assert status == 200
        event_id = exported["data"][-1]["audit_event_id"]

        with _database_connection() as connection:
            with connection.cursor() as cursor:
                with pytest.raises(psycopg2.Error, match="append-only"):
                    cursor.execute("UPDATE audit_event SET action = 'FORGED' WHERE id = %s", (event_id,))
                connection.rollback()
                with pytest.raises(psycopg2.Error, match="append-only"):
                    cursor.execute("DELETE FROM audit_event WHERE id = %s", (event_id,))
                connection.rollback()

    def test_records_transfer_and_credit_advance_in_the_chain(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        origin_key = make_account(customer_key)["response"]["account_key"]
        destination_key = make_account(customer_key)["response"]["account_key"]
        assert RequestGenerator.POST_transaction(
            origin_key, {"type": "DEPOSIT", "amount": 500}
        )[0] == 201
        status, transfer = RequestGenerator.POST_transaction(
            origin_key,
            {
                "type": "TRANSFER",
                "amount": 200,
                "destination_account_key": destination_key,
            },
        )
        assert status == 201

        advance_account_key = make_account(customer_key)["response"]["account_key"]
        expect_bankslip_ok()
        status, plan = RequestGenerator.POST_billing_plan(
            advance_account_key,
            {"base_amount": 1000, "first_due_date": "2027-01-31"},
        )
        assert status == 201
        status, advance = RequestGenerator.POST_credit_advance(
            advance_account_key, {"bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
        )
        assert status == 201

        status, exported = RequestGenerator.GET_audit_events()
        assert status == 200
        actions = {(event["action"], event["resource_key"]) for event in exported["data"]}
        assert ("TRANSFER_CREATED", transfer["transaction_key"]) in actions
        assert ("CREDIT_ADVANCE_CREATED", advance["credit_advance_key"]) in actions
