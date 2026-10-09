"""Métricas Prometheus com rótulos deliberadamente de baixa cardinalidade."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "baas_http_requests",
    "Quantidade de respostas HTTP produzidas pela API.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "baas_http_request_duration_seconds",
    "Duração das requisições HTTP em segundos.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
QIT_ERRORS = Counter(
    "baas_qit_errors",
    "Quantidade de erros de domínio por código QIT.",
    ["code", "route"],
    registry=REGISTRY,
)
CONNECTOR_FAILURES = Counter(
    "baas_external_connector_failures",
    "Falhas de conectores externos por conector.",
    ["connector"],
    registry=REGISTRY,
)
IDEMPOTENCY_REPLAYS = Counter(
    "baas_idempotency_replays",
    "Repetições seguras respondidas pela camada de idempotência.",
    ["scope"],
    registry=REGISTRY,
)
LOCK_WAIT = Histogram(
    "baas_database_lock_wait_seconds",
    "Tempo observado ao adquirir consulta que pode disputar uma trava PostgreSQL.",
    ["operation"],
    registry=REGISTRY,
)
ACTIVE_SESSIONS = Gauge(
    "baas_active_user_sessions",
    "Sessões de usuário não revogadas e ainda não expiradas no instante da coleta.",
    registry=REGISTRY,
)
OUTBOX_PENDING = Gauge(
    "baas_outbox_pending_events",
    "Eventos ainda não publicados pela outbox no instante da coleta.",
    registry=REGISTRY,
)
OUTBOX_RETRYING = Gauge(
    "baas_outbox_retrying_events",
    "Eventos pendentes que já falharam ao menos uma entrega.",
    registry=REGISTRY,
)
OUTBOX_DELIVERY_ATTEMPTS = Gauge(
    "baas_outbox_delivery_attempts_total",
    "Soma persistida das tentativas de entrega da outbox.",
    registry=REGISTRY,
)


def record_http_request(method: str, route: str, status: int, duration_seconds: float) -> None:
    labels = {"method": method, "route": route, "status": str(status)}
    HTTP_REQUESTS.labels(**labels).inc()
    HTTP_DURATION.labels(**labels).observe(duration_seconds)


def record_qit_error(code: str, route: str) -> None:
    QIT_ERRORS.labels(code=code, route=route).inc()


def record_connector_failure(connector: str) -> None:
    CONNECTOR_FAILURES.labels(connector=connector).inc()


def record_idempotency_replay(scope: str) -> None:
    IDEMPOTENCY_REPLAYS.labels(scope=scope).inc()


def observe_lock_wait(operation: str, seconds: float) -> None:
    LOCK_WAIT.labels(operation=operation).observe(seconds)


def set_active_sessions(count: int) -> None:
    ACTIVE_SESSIONS.set(count)


def set_outbox_state(pending: int, retrying: int, delivery_attempts: int) -> None:
    OUTBOX_PENDING.set(pending)
    OUTBOX_RETRYING.set(retrying)
    OUTBOX_DELIVERY_ATTEMPTS.set(delivery_attempts)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)
