import time
import re

from fastapi import FastAPI, Request

from constants import BYPASS_ENDPOINTS
from utils.logger import get_logger
from utils.metrics import record_http_request
from utils.authentication import decode_access_token


logger = get_logger(__name__)
ACCOUNT_PATH = re.compile(r"^/account/([^/]+)")


def _mask_key(value: str) -> str:
    return f"{value[:6]}…{value[-4:]}" if len(value) > 10 else "***"


def _account_key_from_path(path: str) -> str | None:
    match = ACCOUNT_PATH.match(path)
    return _mask_key(match.group(1)) if match else None


def _user_key_from_authorization(authorization: str | None) -> str | None:
    if not authorization:
        return None
    try:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        return _mask_key(decode_access_token(token)["sub"])
    except (KeyError, ValueError):
        return None


def register_request_logger_middleware(application: FastAPI) -> None:
    """Escreve no log toda requisição que entra e toda resposta que sai.

    Quando algo der errado em produção, é esta linha de log que conta
    a história: qual rota, qual status, quanto tempo demorou — e, no
    colchete que o logger acrescenta sozinho, o identificador da
    requisição, que junta as duas linhas (a de entrada e a de saída) e
    tudo o que aconteceu entre elas.

    Duas coisas que este middleware NÃO faz, de propósito:

    • **Não escreve o corpo da requisição no log.** É tentador, e é
      assim que dado sensível vaza: senha, documento, número de cartão
      — tudo o que o cliente mandou ficaria gravado em texto puro num
      arquivo que muita gente lê e que ninguém trata como confidencial.
      Se um dia você precisar logar o corpo, logue campo escolhido a
      dedo, nunca o objeto inteiro.

    • **Não fala das rotas de BYPASS_ENDPOINTS.** O Docker consulta o
      /health_check a cada três segundos; sem esta linha, o log seria
      quase só isso.
    """

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        if request.url.path in BYPASS_ENDPOINTS:
            return await call_next(request)

        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_seconds = time.perf_counter() - started_at
        elapsed_ms = elapsed_seconds * 1000
        route = getattr(request.scope.get("route"), "path", None) or "unmatched"
        if request.url.path != "/metrics":
            record_http_request(request.method, route, response.status_code, elapsed_seconds)
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "method": request.method,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(elapsed_ms, 3),
                "account_key": _account_key_from_path(request.url.path),
                "user_key": _user_key_from_authorization(request.headers.get("Authorization")),
            },
        )

        return response
