from models import AuditEvent
from database import Context


class AuditRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_all(self) -> list[AuditEvent]:
        return self.session.query(AuditEvent).order_by(AuditEvent.id.asc()).all()

    def get_checkpoint(self) -> AuditEvent | None:
        return self.session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
