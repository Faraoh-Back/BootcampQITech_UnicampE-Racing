"""A S15 é verificada sem importar código da aplicação (guardião R1)."""

from os import environ
from pathlib import Path
import subprocess
import sys

import psycopg2

from tests.utils import mock_server
from tests.utils.requisition import ClientRequisition
from tests.utils.request_generator import RequestGenerator


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _database_connection():
    url = environ.get(
        "DATABASE_URL", "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"
    )
    return psycopg2.connect(url.replace("postgresql+psycopg2://", "postgresql://", 1))


def _get_event(account_key: str, status: str) -> tuple:
    with _database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_key, topic, payload, delivery_attempts, published_at, last_error
                FROM outbox_event
                WHERE aggregate_key = %s AND payload->>'status' = %s
                ORDER BY id DESC LIMIT 1
                """,
                (account_key, status),
            )
            event = cursor.fetchone()
    assert event is not None
    return event


def _run_worker(batch_size: int = 100) -> None:
    worker_env = environ.copy()
    worker_env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    worker_env["DATABASE_URL"] = worker_env.get(
        "DATABASE_URL", "postgresql+psycopg2://bootcamp:bootcamp@localhost:5432/bootcamp"
    )
    worker_env["NOTIFICATION_WEBHOOK_URL"] = (
        f"http://{worker_env.get('SERVER_LOCALHOST', '0.0.0.0')}:"
        f"{worker_env.get('MOCK_PORT', '1080')}/notifications"
    )
    subprocess.run(
        [sys.executable, "-m", "workers.outbox_publisher", "--once", "--batch-size", str(batch_size)],
        cwd=PROJECT_ROOT,
        env=worker_env,
        check=True,
        capture_output=True,
        text=True,
    )


class TestOutbox:
    def test_status_change_commits_domain_event_and_outbox_together(self, make_account):
        account = make_account()
        account_key = account["response"]["account_key"]

        status, body = RequestGenerator.PUT_account_block(account_key)

        assert status == 200
        assert body["status"] == "BLOCKED"
        event_key, topic, payload, attempts, published_at, last_error = _get_event(account_key, "BLOCKED")
        assert event_key
        assert topic == "account.status_changed"
        assert payload == {
            "account_key": account_key,
            "customer_key": account["customer_key"],
            "previous_status": "APPROVED",
            "status": "BLOCKED",
        }
        assert attempts == 0
        assert published_at is None
        assert last_error is None

    def test_worker_delivers_once_and_does_not_republish_success(self, make_account):
        mock_server.reset()
        mock_server.expect_notification()
        account_key = make_account()["response"]["account_key"]
        assert RequestGenerator.PUT_account_block(account_key)[0] == 200
        event_key = _get_event(account_key, "BLOCKED")[0]

        _run_worker()
        mock_server.verify_notification_event(event_key)
        delivered = _get_event(account_key, "BLOCKED")
        assert delivered[3] == 1
        assert delivered[4] is not None
        assert delivered[5] is None

        _run_worker()
        mock_server.verify_notification_event(event_key)

    def test_failed_delivery_is_recorded_and_can_be_retried(self, make_account):
        mock_server.reset()  # sem expectativa: o MockServer devolve erro e o worker não confirma entrega
        account_key = make_account()["response"]["account_key"]
        assert RequestGenerator.PUT_account_cancel(account_key)[0] == 200
        event_key = _get_event(account_key, "CANCELLED")[0]

        _run_worker()
        failed = _get_event(account_key, "CANCELLED")
        assert failed[3] == 1
        assert failed[4] is None
        assert failed[5]

        metrics = ClientRequisition.send("GET", "/metrics", headers={"INTERNAL-TOKEN": "default_token"})
        assert metrics.response_status == 200
        assert b"baas_outbox_pending_events" in metrics.response_content
        assert b"baas_outbox_retrying_events" in metrics.response_content
        assert b"baas_outbox_delivery_attempts_total" in metrics.response_content

        # A espera exponencial é parte da retentativa; avançamos apenas este
        # evento no banco de teste para provar o segundo envio sem aguardar.
        with _database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE outbox_event SET next_attempt_at = NOW() WHERE event_key = %s", (event_key,))
            connection.commit()

        mock_server.expect_notification()
        _run_worker()
        # A primeira chamada chegou ao destino, mas recebeu 404; a segunda é
        # a entrega bem-sucedida do mesmo event_key, que o consumidor deduplica.
        mock_server.verify_notification_event(event_key, times=2)
        retried = _get_event(account_key, "CANCELLED")
        assert retried[3] == 2
        assert retried[4] is not None
        assert retried[5] is None
