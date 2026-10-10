"""Contratos PostgreSQL/upgrade, separados da evidência estritamente HTTP."""

from os import environ
from pathlib import Path
from uuid import uuid4

import psycopg2
from psycopg2 import errors, sql
import pytest

from tests.integration.credit_advance.test_positive_net import publish_price, receivables, reset_mockserver
from tests.utils.request_generator import RequestGenerator


def connect():
    url = environ.get("DATABASE_URL",
        "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp")
    return psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1))


@pytest.fixture
def db():
    connection = connect()
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def account_id(make_account, db):
    account = make_account()
    assert account["status"] == 201
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM account WHERE account_key = %s",
            (account["response"]["account_key"],))
        return cursor.fetchone()[0]


def insert_advance(cursor, account_id, net):
    cursor.execute("""
        INSERT INTO credit_advance
            (credit_advance_key, account_id, gross_amount, fee_amount, net_amount)
        VALUES (%s, %s, 10000, %s, %s) RETURNING id
        """, (str(uuid4()), account_id, 10000 - net, net))
    return cursor.fetchone()[0]


def insert_quote(cursor, account_id, operation, net):
    cursor.execute("""
        INSERT INTO quote (quote_key, account_id, operation, request_hash,
            gross_amount, fee_amount, net_amount, pricing_policy_key,
            pricing_version, risk_policy_key, risk_version, expires_at)
        VALUES (%s, %s, %s, %s, 10000, %s, %s, %s, 1, %s, 1,
            NOW() + INTERVAL '60 seconds') RETURNING id
        """, (str(uuid4()), account_id, operation, "0" * 64, 10000 - net,
            net, str(uuid4()), str(uuid4())))
    return cursor.fetchone()[0]


@pytest.mark.parametrize("net", [0, -2000, 1])
def test_database_enforces_positive_advance_on_insert(db, account_id, net):
    with db.cursor() as cursor:
        if net > 0:
            assert insert_advance(cursor, account_id, net) > 0
        else:
            with pytest.raises(errors.CheckViolation) as caught:
                insert_advance(cursor, account_id, net)
            assert caught.value.diag.constraint_name == "chk_credit_advance_positive_net"


@pytest.mark.parametrize("net", [0, -2000])
def test_database_enforces_positive_advance_on_update(db, account_id, net):
    with db.cursor() as cursor:
        advance_id = insert_advance(cursor, account_id, 9700)
        with pytest.raises(errors.CheckViolation) as caught:
            cursor.execute("UPDATE credit_advance SET fee_amount = %s, net_amount = %s WHERE id = %s",
                (10000 - net, net, advance_id))
        assert caught.value.diag.constraint_name == "chk_credit_advance_positive_net"


@pytest.mark.parametrize("update", [False, True], ids=["insert", "update"])
def test_database_enforces_positive_credit_advance_quote(db, account_id, update):
    with db.cursor() as cursor:
        quote_id = insert_quote(cursor, account_id, "CREDIT_ADVANCE", 9700) if update else None
        with pytest.raises(errors.CheckViolation) as caught:
            if update:
                cursor.execute("UPDATE quote SET fee_amount = 10000, net_amount = 0 WHERE id = %s", (quote_id,))
            else:
                insert_quote(cursor, account_id, "CREDIT_ADVANCE", 0)
        assert caught.value.diag.constraint_name == "chk_quote_credit_advance_positive_net"


def test_new_constraint_does_not_apply_advance_business_rule_to_transfer_quote(db, account_id):
    with db.cursor() as cursor:
        assert insert_quote(cursor, account_id, "TRANSFER", 0) > 0


def persisted_state(db, account_key):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, customer_id, balance FROM account WHERE account_key = %s", (account_key,))
        account_id, customer_id, balance = cursor.fetchone()
        counts = [balance]
        for table in ("credit_advance", "quote", "transaction", "idempotency_key"):
            cursor.execute(sql.SQL("SELECT count(*) FROM {} WHERE account_id = %s").format(sql.Identifier(table)), (account_id,))
            counts.append(cursor.fetchone()[0])
        for table in ("pricing_snapshot", "risk_policy_snapshot"):
            # O fallback tem customer_id NULL: não omitir seus snapshots.
            cursor.execute(sql.SQL("SELECT count(*) FROM {} WHERE customer_id = %s OR customer_id IS NULL").format(sql.Identifier(table)), (customer_id,))
            counts.append(cursor.fetchone()[0])
        cursor.execute("SELECT count(*) FROM audit_event")
        counts.append(cursor.fetchone()[0])
        cursor.execute("""SELECT b.id, b.credit_advance_id FROM bank_slip b
            JOIN billing_plan p ON p.id = b.billing_plan_id
            WHERE p.account_id = %s ORDER BY b.id""", (account_id,))
        counts.append(cursor.fetchall())
        return counts


@pytest.mark.parametrize("fixed_fee,basis_points", [
    pytest.param(10000, 0, id="zero-net"),
    pytest.param(12000, 0, id="negative-net"),
    pytest.param(9223372036854775807, 1, id="computed-fee-exceeds-bigint"),
])
@pytest.mark.parametrize("quote", [False, True], ids=["execution", "quote"])
def test_business_rejection_rolls_back_all_persisted_effects(db, receivables, fixed_fee, basis_points, quote):
    customer, account, plan = receivables(initial_balance=50000)
    publish_price(customer, fixed_fee, basis_points)
    before = persisted_state(db, account)
    payload = {"bank_slip_keys": [plan["bank_slips"][0]["bank_slip_key"]]}
    if quote:
        status, response = RequestGenerator.POST_quote(account, {"operation": "CREDIT_ADVANCE", **payload})
    else:
        status, response = RequestGenerator.POST_credit_advance(account, payload)
    assert status == 422
    assert response["code"] == "QIT001030"
    assert persisted_state(db, account) == before


@pytest.mark.parametrize("legacy", [False, True], ids=["clean-upgrade", "preserve-legacy"])
def test_targeted_upgrade_is_idempotent_preserves_history_and_protects_new_writes(legacy):
    # Schema exclusivo: nunca remove constraints nem fatos do domínio real.
    schema_name = "test_positive_net_" + uuid4().hex
    connection = connect()
    connection.autocommit = True
    migration = (Path(__file__).resolve().parents[3] /
        "database/migrations/20261010_positive_credit_advance_net.sql").read_text()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
            cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name)))
            cursor.execute("CREATE TABLE credit_advance (net_amount BIGINT NOT NULL)")
            cursor.execute("CREATE TABLE quote (operation VARCHAR(40) NOT NULL, net_amount BIGINT NOT NULL)")
            cursor.execute("INSERT INTO credit_advance VALUES (9700)")
            cursor.execute("INSERT INTO quote VALUES ('CREDIT_ADVANCE', 9700), ('TRANSFER', 0)")
            if legacy:
                cursor.execute("INSERT INTO credit_advance VALUES (0), (-2000)")
                cursor.execute("INSERT INTO quote VALUES ('CREDIT_ADVANCE', 0), ('CREDIT_ADVANCE', -2000)")
            cursor.execute("SELECT net_amount FROM credit_advance ORDER BY net_amount")
            old_advances = cursor.fetchall()
            cursor.execute("SELECT operation, net_amount FROM quote ORDER BY operation, net_amount")
            old_quotes = cursor.fetchall()
            for _ in range(2):
                cursor.execute(migration)
                cursor.execute("SELECT net_amount FROM credit_advance ORDER BY net_amount")
                assert cursor.fetchall() == old_advances
                cursor.execute("SELECT operation, net_amount FROM quote ORDER BY operation, net_amount")
                assert cursor.fetchall() == old_quotes
                cursor.execute("""SELECT conname, convalidated FROM pg_constraint
                    WHERE conrelid IN ('credit_advance'::regclass, 'quote'::regclass) ORDER BY conname""")
                assert cursor.fetchall() == [
                    ("chk_credit_advance_positive_net", not legacy),
                    ("chk_quote_credit_advance_positive_net", not legacy),
                ]
            for net in (0, -2000):
                with pytest.raises(errors.CheckViolation):
                    cursor.execute("INSERT INTO credit_advance VALUES (%s)", (net,))
                with pytest.raises(errors.CheckViolation):
                    cursor.execute("INSERT INTO quote VALUES ('CREDIT_ADVANCE', %s)", (net,))
            cursor.execute("INSERT INTO credit_advance VALUES (1)")
            cursor.execute("INSERT INTO quote VALUES ('CREDIT_ADVANCE', 1), ('TRANSFER', 0)")
    finally:
        # Desfaz também BEGIN abortado antes de remover só o schema sintético.
        with connection.cursor() as cursor:
            cursor.execute("ROLLBACK")
            cursor.execute("SET search_path TO public")
            cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))
        connection.close()
