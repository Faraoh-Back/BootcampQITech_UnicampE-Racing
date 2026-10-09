from models import AuditEvent


class AuditEventDTO:
    @staticmethod
    def obj_to_dict(event: AuditEvent) -> dict:
        return {
            "audit_event_id": event.id,
            "actor_type": event.actor_type,
            "actor_key": event.actor_key,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_key": event.resource_key,
            "request_id": event.request_id,
            "origin": event.origin,
            "previous_summary": event.previous_summary,
            "current_summary": event.current_summary,
            "previous_hash": event.previous_hash,
            "event_hash": event.event_hash,
            "event_datetime": event.event_datetime,
        }
