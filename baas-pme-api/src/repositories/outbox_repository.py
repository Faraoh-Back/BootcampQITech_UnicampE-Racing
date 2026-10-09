"""Persistência e lease dos eventos de saída."""

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from models import OutboxEvent


class OutboxRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self, topic: str, aggregate_type: str, aggregate_key: str, payload: dict) -> OutboxEvent:
        event = OutboxEvent(
            event_key=str(uuid4()),
            topic=topic,
            aggregate_type=aggregate_type,
            aggregate_key=aggregate_key,
            payload=payload,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def claim_pending(self, limit: int, lease_seconds: int) -> list[OutboxEvent]:
        now = datetime.utcnow()
        events = (
            self.session.query(OutboxEvent)
            .filter(
                OutboxEvent.published_at.is_(None),
                OutboxEvent.next_attempt_at <= now,
                or_(OutboxEvent.locked_until.is_(None), OutboxEvent.locked_until < now),
            )
            .order_by(OutboxEvent.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )
        for event in events:
            event.lock_token = str(uuid4())
            event.locked_until = now + timedelta(seconds=lease_seconds)
        self.session.flush()
        return events

    def mark_published(self, event_key: str, lock_token: str) -> bool:
        event = (
            self.session.query(OutboxEvent)
            .filter(OutboxEvent.event_key == event_key, OutboxEvent.lock_token == lock_token)
            .with_for_update()
            .first()
        )
        if event is None or event.published_at is not None:
            return False
        event.delivery_attempts += 1
        event.published_at = datetime.utcnow()
        event.lock_token = None
        event.locked_until = None
        event.last_error = None
        return True

    def mark_failed(self, event_key: str, lock_token: str, error: str, retry_base_seconds: int) -> bool:
        event = (
            self.session.query(OutboxEvent)
            .filter(OutboxEvent.event_key == event_key, OutboxEvent.lock_token == lock_token)
            .with_for_update()
            .first()
        )
        if event is None or event.published_at is not None:
            return False
        event.delivery_attempts += 1
        delay_seconds = min(retry_base_seconds * (2 ** (event.delivery_attempts - 1)), 300)
        event.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        event.last_error = error[:500]
        event.lock_token = None
        event.locked_until = None
        return True

    def count_pending(self) -> int:
        return self.session.query(OutboxEvent).filter(OutboxEvent.published_at.is_(None)).count()

    def metric_state(self) -> tuple[int, int, int]:
        pending = self.count_pending()
        retrying = (
            self.session.query(OutboxEvent)
            .filter(OutboxEvent.published_at.is_(None), OutboxEvent.delivery_attempts > 0)
            .count()
        )
        attempts = self.session.query(func.coalesce(func.sum(OutboxEvent.delivery_attempts), 0)).scalar()
        return pending, retrying, int(attempts)
