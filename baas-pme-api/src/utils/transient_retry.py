"""Retentativa de transação para os poucos erros PostgreSQL realmente transitórios.

Não é um mecanismo de esperar saldo, status ou conector externo. A operação só
recomeça quando o PostgreSQL abortou integralmente a tentativa por deadlock ou
serialização; a mesma Idempotency-Key continua identificando a operação lógica.
"""

from collections.abc import Callable
import random
import time
from typing import TypeVar

from sqlalchemy.exc import OperationalError

from constants import (
    DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS,
    DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS,
)
from database import get_context
from errors import DatabaseTransientFailure
from utils.metrics import record_database_transient_retry


Result = TypeVar("Result")
TRANSIENT_POSTGRES_CODES = {"40P01": "deadlock", "40001": "serialization"}


def _postgres_cause(error: OperationalError) -> str | None:
    return TRANSIENT_POSTGRES_CODES.get(getattr(error.orig, "pgcode", None))


def _discard_failed_session() -> None:
    """Fecha a sessão abortada para a próxima tentativa nascer realmente nova."""
    context = get_context()
    session = context.db_session
    if session is None:
        return
    try:
        session.rollback()
    finally:
        session.close()
        context.db_session = None


def execute_with_transient_retry(operation: Callable[[], Result]) -> Result:
    """Executa uma operação idempotente em novas transações quando o PG a aborta.

    O chamador deve criar controller dentro de ``operation``. Assim, após o
    rollback, repositories, AuditRecorder e Session SQLAlchemy também são novos.
    """
    for attempt in range(1, DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS + 1):
        try:
            return operation()
        except OperationalError as error:
            cause = _postgres_cause(error)
            if cause is None:
                raise

            _discard_failed_session()
            if attempt == DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS:
                raise DatabaseTransientFailure() from error

            record_database_transient_retry(cause)
            delay_seconds = (DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS / 1000) * (2 ** (attempt - 1))
            if delay_seconds:
                time.sleep(delay_seconds * random.uniform(0.5, 1.5))
