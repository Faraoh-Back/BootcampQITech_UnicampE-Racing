"""Grava eventos de auditoria na mesma transação do fato de negócio."""

from datetime import datetime
from hashlib import sha256
import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import AuditEvent
from utils.request_context import get_audit_actor, get_request_id, get_request_origin


GENESIS_HASH = "0" * 64
# Uma chave estável e exclusiva do produto para pg_advisory_xact_lock.
# Ela serializa somente a montagem da cadeia, não as regras de saldo.
AUDIT_CHAIN_LOCK = 875_120_411


def canonical_event_payload(
    *,
    actor_type: str,
    actor_key: str,
    action: str,
    resource_type: str,
    resource_key: str,
    request_id: str,
    origin: str,
    previous_summary: dict | None,
    current_summary: dict | None,
    previous_hash: str,
    event_datetime: datetime,
) -> bytes:
    """Representação pública e determinística coberta pelo hash da cadeia."""
    payload = {
        "actor_key": actor_key,
        "actor_type": actor_type,
        "action": action,
        "current_summary": current_summary,
        "event_datetime": event_datetime.isoformat(timespec="microseconds"),
        "origin": origin,
        "previous_hash": previous_hash,
        "previous_summary": previous_summary,
        "request_id": request_id,
        "resource_key": resource_key,
        "resource_type": resource_type,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class AuditRecorder:
    """Acrescenta um evento e nunca altera um já gravado."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        action: str,
        resource_type: str,
        resource_key: str,
        previous_summary: dict | None = None,
        current_summary: dict | None = None,
    ) -> AuditEvent:
        # Sem essa trava, duas primeiras inserções concorrentes poderiam ambas
        # enxergar a mesma ponta da cadeia. O lock dura apenas até o commit
        # desta própria transação e impede bifurcação silenciosa.
        self.session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": AUDIT_CHAIN_LOCK})
        last_event = self.session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        previous_hash = last_event.event_hash if last_event is not None else GENESIS_HASH
        actor_type, actor_key = get_audit_actor()
        event_datetime = datetime.utcnow()
        event_hash = sha256(
            canonical_event_payload(
                actor_type=actor_type,
                actor_key=actor_key,
                action=action,
                resource_type=resource_type,
                resource_key=resource_key,
                request_id=get_request_id(),
                origin=get_request_origin(),
                previous_summary=previous_summary,
                current_summary=current_summary,
                previous_hash=previous_hash,
                event_datetime=event_datetime,
            )
        ).hexdigest()
        event = AuditEvent(
            actor_type=actor_type,
            actor_key=actor_key,
            action=action,
            resource_type=resource_type,
            resource_key=resource_key,
            request_id=get_request_id(),
            origin=get_request_origin(),
            previous_summary=previous_summary,
            current_summary=current_summary,
            previous_hash=previous_hash,
            event_hash=event_hash,
            event_datetime=event_datetime,
        )
        self.session.add(event)
        self.session.flush()
        return event
