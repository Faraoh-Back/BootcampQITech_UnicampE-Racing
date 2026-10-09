from controllers.base_controller import BaseController
from dtos.audit_event_dto import AuditEventDTO
from repositories.audit_repository import AuditRepository
from utils.audit import GENESIS_HASH


class AuditController(BaseController):
    """Consulta de exportação; a verificação do hash é reproduzível pelo cliente."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.audit_repository = AuditRepository(self.context)

    def get_all(self) -> dict:
        events = self.audit_repository.get_all()
        checkpoint = events[-1] if events else None
        return {
            "data": [AuditEventDTO.obj_to_dict(event) for event in events],
            "checkpoint": self._checkpoint(checkpoint),
        }

    def get_checkpoint(self) -> dict:
        return self._checkpoint(self.audit_repository.get_checkpoint())

    @staticmethod
    def _checkpoint(event) -> dict:
        if event is None:
            return {"audit_event_id": None, "event_hash": GENESIS_HASH}
        return {"audit_event_id": event.id, "event_hash": event.event_hash}
