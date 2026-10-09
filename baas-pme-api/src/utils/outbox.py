"""Publicação independente e retentável dos eventos da outbox."""

from dataclasses import dataclass

import requests

from constants import (
    NOTIFICATION_WEBHOOK_URL,
    OUTBOX_LEASE_SECONDS,
    OUTBOX_RETRY_BASE_SECONDS,
)
from database import SessionLocal
from repositories.outbox_repository import OutboxRepository
from utils.logger import get_logger


@dataclass(frozen=True)
class PublishResult:
    claimed: int
    published: int
    failed: int


class OutboxPublisher:
    """Envia eventos com entrega pelo menos uma vez e chave idempotente.

    Se o processo cair após o webhook aceitar e antes de marcar a linha como
    publicada, o evento pode ser reenviado. O destinatário recebe `event_key`
    no cabeçalho `Idempotency-Key` e deve deduplicá-lo; assim não prometemos a
    impossível entrega exatamente uma vez entre dois bancos independentes.
    """

    def __init__(self, webhook_url: str = NOTIFICATION_WEBHOOK_URL) -> None:
        self.webhook_url = webhook_url
        self.logger = get_logger(__name__)

    def publish_once(self, batch_size: int = 10) -> PublishResult:
        session = SessionLocal()
        try:
            repository = OutboxRepository(session)
            claimed = repository.claim_pending(batch_size, OUTBOX_LEASE_SECONDS)
            deliveries = [
                (event.event_key, event.lock_token, event.topic, event.aggregate_type, event.aggregate_key, event.payload)
                for event in claimed
            ]
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        published = 0
        failed = 0
        for event_key, lock_token, topic, aggregate_type, aggregate_key, payload in deliveries:
            try:
                response = requests.post(
                    self.webhook_url,
                    json={
                        "event_key": event_key,
                        "topic": topic,
                        "aggregate_type": aggregate_type,
                        "aggregate_key": aggregate_key,
                        "payload": payload,
                    },
                    headers={"Idempotency-Key": event_key},
                    timeout=(1, 5),
                )
                response.raise_for_status()
            except requests.RequestException as error:
                self._mark_failed(event_key, lock_token, str(error))
                failed += 1
                self.logger.warning("OUTBOX DELIVERY FAILED event_key=%s error=%s", event_key, error)
            else:
                self._mark_published(event_key, lock_token)
                published += 1
                self.logger.info("OUTBOX DELIVERED event_key=%s topic=%s", event_key, topic)
        return PublishResult(claimed=len(deliveries), published=published, failed=failed)

    def _mark_published(self, event_key: str, lock_token: str) -> None:
        session = SessionLocal()
        try:
            OutboxRepository(session).mark_published(event_key, lock_token)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mark_failed(self, event_key: str, lock_token: str, error: str) -> None:
        session = SessionLocal()
        try:
            OutboxRepository(session).mark_failed(
                event_key, lock_token, error, OUTBOX_RETRY_BASE_SECONDS
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
