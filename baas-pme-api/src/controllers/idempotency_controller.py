from dataclasses import dataclass
from hashlib import sha256
import json

from database import Context
from errors import IdempotencyConflict
from models import IdempotencyKey
from repositories import IdempotencyRepository


@dataclass(frozen=True)
class IdempotencyResult:
    """Resultado para o controller da operação decidir o próximo passo."""

    action: str
    record: IdempotencyKey
    response_status: int | None = None
    response_body: dict | None = None

    @property
    def should_execute(self) -> bool:
        return self.action == "EXECUTE"

    @property
    def should_replay(self) -> bool:
        return self.action == "REPLAY"


class IdempotencyController:
    """Componente reutilizável para operações idempotentes.

    Ele não confirma nem desfaz a sessão: a operação de negócio chama
    ``store_response`` e faz um único ``commit`` junto com seus lançamentos.
    Assim, uma falha de negócio faz rollback tanto da operação quanto da
    reserva da chave, permitindo uma tentativa posterior legítima.
    """

    def __init__(self, context: Context) -> None:
        self.idempotency_repository = IdempotencyRepository(context)

    def begin(self, account_id: int, scope: str, key: str, payload: dict) -> IdempotencyResult:
        request_hash = self.request_hash(payload)
        record, was_inserted = self.idempotency_repository.insert_or_get(
            account_id, scope, key, request_hash
        )
        if was_inserted:
            return IdempotencyResult(action="EXECUTE", record=record)

        if record.request_hash != request_hash:
            raise IdempotencyConflict()
        if record.response_status is None or record.response_body is None:
            raise RuntimeError("Idempotency record exists without a stored response.")
        return IdempotencyResult(
            action="REPLAY",
            record=record,
            response_status=record.response_status,
            response_body=record.response_body,
        )

    def store_response(self, record: IdempotencyKey, status: int, body: dict) -> None:
        self.idempotency_repository.store_response(record, status, body)

    @staticmethod
    def request_hash(payload: dict) -> str:
        canonical_json = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return sha256(canonical_json.encode("utf-8")).hexdigest()
