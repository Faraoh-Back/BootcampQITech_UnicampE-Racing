from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from database import Context
from models import IdempotencyKey


class IdempotencyRepository:
    """Acesso à chave de idempotência, sem decidir regras HTTP ou de negócio."""

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def insert_or_get(
        self, account_id: int, scope: str, key: str, request_hash: str
    ) -> tuple[IdempotencyKey, bool]:
        """Insere a chave ou devolve a linha que venceu a corrida.

        O ``ON CONFLICT`` usa o índice único do banco. Em PostgreSQL, se
        outra transação estiver usando a mesma chave, este comando aguarda
        a confirmação ou rollback dela; depois disso, o SELECT enxerga a
        linha confirmada e permite ao controller decidir entre replay e
        conflito sem criar uma segunda operação.
        """
        statement = (
            insert(IdempotencyKey)
            .values(
                account_id=account_id,
                scope=scope,
                idempotency_key=key,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    IdempotencyKey.account_id,
                    IdempotencyKey.scope,
                    IdempotencyKey.idempotency_key,
                ]
            )
            .returning(IdempotencyKey.id)
        )
        inserted_id = self.session.execute(statement).scalar_one_or_none()
        if inserted_id is not None:
            return self.session.get(IdempotencyKey, inserted_id), True

        existing = self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.account_id == account_id,
                IdempotencyKey.scope == scope,
                IdempotencyKey.idempotency_key == key,
            )
        ).scalar_one()
        return existing, False

    @staticmethod
    def store_response(record: IdempotencyKey, status: int, body: dict) -> None:
        record.response_status = status
        record.response_body = body
