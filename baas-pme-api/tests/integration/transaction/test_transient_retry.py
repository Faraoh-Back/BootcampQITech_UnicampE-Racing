from os import environ
import re
from uuid import uuid4

import psycopg2
import pytest

from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import INTERNAL_TOKEN, RequestGenerator


def _database_connection():
    url = environ.get(
        "DATABASE_URL", "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"
    )
    return psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1))


def _retry_counter(cause="deadlock") -> float:
    import requests

    response = requests.get(
        f"http://{environ.get('SERVER_LOCALHOST', '0.0.0.0')}:{environ.get('API_PORT', '3000')}/metrics",
        headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        timeout=3,
    )
    assert response.status_code == 200
    match = re.search(
        rf'^baas_database_transient_retries_total\{{cause="{cause}"\}} ([0-9.e+-]+)$',
        response.text,
        re.MULTILINE,
    )
    return float(match.group(1)) if match else 0.0


class TestTransientTransactionRetry:
    @pytest.mark.parametrize("sqlstate,cause", [("40P01", "deadlock"), ("40001", "serialization")])
    def test_retries_transient_failure_once_with_one_financial_effect(self, make_account, sqlstate, cause):
        account_key = make_account()["response"]["account_key"]
        before = _retry_counter(cause)

        with _database_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    # nextval is intentionally not rolled back by PostgreSQL.
                    # The trigger makes only the first INSERT fail with the same
                    # SQLSTATE de deadlock/serialização, então permite o retry.
                    cursor.execute("CREATE SEQUENCE transient_retry_once_seq START WITH 1")
                    cursor.execute(
                        """
                        CREATE FUNCTION transient_retry_once() RETURNS trigger AS $$
                        BEGIN
                            IF nextval('transient_retry_once_seq') = 1 THEN
                                RAISE EXCEPTION 'synthetic transient deadlock'
                                    USING ERRCODE = %s;
                            END IF;
                            RETURN NEW;
                        END;
                        $$ LANGUAGE plpgsql
                        """,
                        (sqlstate,),
                    )
                    cursor.execute(
                        'CREATE TRIGGER transient_retry_once_trigger '
                        'BEFORE INSERT ON "transaction" '
                        'FOR EACH ROW EXECUTE FUNCTION transient_retry_once()'
                    )
                connection.commit()

                response = ClientRequisition.send(
                    "POST",
                    f"/account/{account_key}/transaction",
                    payload={"type": "DEPOSIT", "amount": 100},
                    headers={
                        "INTERNAL-TOKEN": INTERNAL_TOKEN,
                        "Idempotency-Key": str(uuid4()),
                    },
                )
                assert response.response_status == 201
                assert response.response_json["amount"] == 100
            finally:
                with connection.cursor() as cursor:
                    cursor.execute('DROP TRIGGER IF EXISTS transient_retry_once_trigger ON "transaction"')
                    cursor.execute("DROP FUNCTION IF EXISTS transient_retry_once()")
                    cursor.execute("DROP SEQUENCE IF EXISTS transient_retry_once_seq")
                connection.commit()

        assert _retry_counter(cause) == before + 1
        assert RequestGenerator.GET_account(account_key)[1]["balance"] == 100
        status, statement = RequestGenerator.GET_transactions(account_key)
        assert status == 200
        assert len(statement["data"]) == 1

    def test_business_failure_is_not_retried(self, make_account):
        account_key = make_account()["response"]["account_key"]
        before = _retry_counter()

        response = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/transaction",
            payload={"type": "WITHDRAWAL", "amount": 100},
            headers={
                "INTERNAL-TOKEN": INTERNAL_TOKEN,
                "Idempotency-Key": str(uuid4()),
            },
        )

        assert response.response_status == 422
        assert response.response_json["code"] == "QIT001005"
        assert _retry_counter() == before
        assert RequestGenerator.GET_account(account_key)[1]["balance"] == 0

    @pytest.mark.parametrize("sqlstate", ["40P01", "40001"])
    def test_reports_retry_exhaustion_without_financial_effect(self, make_account, sqlstate):
        account_key = make_account()["response"]["account_key"]

        with _database_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE FUNCTION transient_retry_exhausted() RETURNS trigger AS $$
                        BEGIN
                            RAISE EXCEPTION 'synthetic persistent deadlock'
                                USING ERRCODE = %s;
                        END;
                        $$ LANGUAGE plpgsql
                        """,
                        (sqlstate,),
                    )
                    cursor.execute(
                        'CREATE TRIGGER transient_retry_exhausted_trigger '
                        'BEFORE INSERT ON "transaction" '
                        'FOR EACH ROW EXECUTE FUNCTION transient_retry_exhausted()'
                    )
                connection.commit()

                response = ClientRequisition.send(
                    "POST",
                    f"/account/{account_key}/transaction",
                    payload={"type": "DEPOSIT", "amount": 100},
                    headers={
                        "INTERNAL-TOKEN": INTERNAL_TOKEN,
                        "Idempotency-Key": str(uuid4()),
                    },
                )
                assert response.response_status == 503
                assert response.response_json["code"] == "QIT001025"
            finally:
                with connection.cursor() as cursor:
                    cursor.execute('DROP TRIGGER IF EXISTS transient_retry_exhausted_trigger ON "transaction"')
                    cursor.execute("DROP FUNCTION IF EXISTS transient_retry_exhausted()")
                connection.commit()

        assert RequestGenerator.GET_account(account_key)[1]["balance"] == 0
        status, statement = RequestGenerator.GET_transactions(account_key)
        assert status == 200
        assert statement["data"] == []

    def test_unexpected_failure_is_sanitized_and_rolls_back_entire_operation(self, make_account):
        account_key = make_account()["response"]["account_key"]
        idempotency_key = str(uuid4())
        payload = {"type": "DEPOSIT", "amount": 100}
        before = _retry_counter() + _retry_counter("serialization")
        sensitive_diagnostic = "private-db-diagnostic-never-return-to-client"

        with _database_connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE FUNCTION unexpected_financial_failure() RETURNS trigger AS $$
                        BEGIN
                            IF (SELECT account_key FROM account WHERE id = NEW.account_id) = %s THEN
                                RAISE EXCEPTION %s;
                            END IF;
                            RETURN NEW;
                        END;
                        $$ LANGUAGE plpgsql
                        """,
                        (account_key, sensitive_diagnostic),
                    )
                    cursor.execute(
                        'CREATE TRIGGER unexpected_financial_failure_trigger '
                        'BEFORE INSERT ON "transaction" '
                        'FOR EACH ROW EXECUTE FUNCTION unexpected_financial_failure()'
                    )
                connection.commit()
                response = ClientRequisition.send(
                    "POST", f"/account/{account_key}/transaction", payload=payload,
                    headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Idempotency-Key": idempotency_key},
                )
                assert response.response_status == 500
                assert set(response.response_json) == {"title", "description", "translation", "code"}
                assert response.response_json["code"] == "QIT000500"
                assert sensitive_diagnostic not in response.response.text
                assert _retry_counter() + _retry_counter("serialization") == before
                assert RequestGenerator.GET_account(account_key)[1]["balance"] == 0
                assert RequestGenerator.GET_transactions(account_key)[1]["data"] == []
            finally:
                with connection.cursor() as cursor:
                    cursor.execute('DROP TRIGGER IF EXISTS unexpected_financial_failure_trigger ON "transaction"')
                    cursor.execute("DROP FUNCTION IF EXISTS unexpected_financial_failure()")
                connection.commit()

        # A reserva idempotente abortada não pode impedir a retomada segura.
        status, result = RequestGenerator.POST_transaction(account_key, payload, idempotency_key=idempotency_key)
        assert status == 201
        assert RequestGenerator.POST_transaction(account_key, payload, idempotency_key=idempotency_key) == (201, result)
        assert RequestGenerator.GET_account(account_key)[1]["balance"] == 100
        assert len(RequestGenerator.GET_transactions(account_key)[1]["data"]) == 1
