"""Regra de janela noturna para saques e transferências."""

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from constants import NIGHT_END, NIGHT_START, NIGHT_TIME_OVERRIDE, TIMEZONE


def is_night_window() -> bool:
    """Informa se a hora atual está na janela que cruza a meia-noite.

    ``NIGHT_TIME_OVERRIDE`` é intencionalmente uma variável de ambiente, não
    um parâmetro HTTP: ela torna o ambiente de teste reprodutível sem abrir
    uma superfície de API que permitiria ao cliente escolher o próprio relógio.
    """
    start, end = validate_night_configuration()

    now = _current_time()
    if start < end:
        return start <= now < end
    return now >= start or now < end


def validate_night_configuration() -> tuple[time, time]:
    """Valida a configuração na inicialização, antes de atender requisições."""
    start = _parse_time(NIGHT_START, "NIGHT_START")
    end = _parse_time(NIGHT_END, "NIGHT_END")
    if start == end:
        raise EnvironmentError("NIGHT_START and NIGHT_END must define a non-empty night window.")
    if NIGHT_TIME_OVERRIDE is not None:
        _parse_time(NIGHT_TIME_OVERRIDE, "NIGHT_TIME_OVERRIDE")
    else:
        try:
            ZoneInfo(TIMEZONE)
        except ZoneInfoNotFoundError as error:
            raise EnvironmentError(f"TIMEZONE is not a valid IANA timezone: {TIMEZONE}.") from error
    return start, end


def _current_time() -> time:
    if NIGHT_TIME_OVERRIDE is not None:
        return _parse_time(NIGHT_TIME_OVERRIDE, "NIGHT_TIME_OVERRIDE")
    try:
        # Os limites de ambiente são horas locais sem tzinfo. Normalizamos a
        # hora do datetime consciente para a comparação não misturar objetos
        # conscientes e inocentes de fuso.
        return datetime.now(ZoneInfo(TIMEZONE)).time().replace(tzinfo=None)
    except ZoneInfoNotFoundError as error:
        raise EnvironmentError(f"TIMEZONE is not a valid IANA timezone: {TIMEZONE}.") from error


def _parse_time(value: str, variable_name: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise EnvironmentError(f"{variable_name} must use HH:MM or HH:MM:SS format.") from error
