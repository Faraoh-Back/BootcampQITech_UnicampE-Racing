import os


SERVICE_ROOT = os.path.abspath(os.path.dirname(__file__))

# Onde moram os arquivos de schema — os .json que descrevem o formato
# que cada requisicao precisa ter. Quem le essa pasta e o
# src/utils/schema_handler.py.
SCHEMA_PATH = os.path.join(SERVICE_ROOT, "schemas")

APP_ENV = os.environ.get("APP_ENV", "local")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "bootcamp-api")

DATABASE_URL = os.environ.get("DATABASE_URL")
INTERNAL_TOKEN = os.environ.get("INTERNAL_TOKEN")
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ACCESS_TOKEN_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_MINUTES", "15"))
JWT_SESSION_MAX_HOURS = int(os.environ.get("JWT_SESSION_MAX_HOURS", "8"))

# A API de boletos: o serviço de fora que este projeto chama pra emitir
# uma cobrança (veja src/connectors/). O endereço vem do ambiente, como
# tudo aqui — na sua máquina ele aponta pro mock server do sábado 4; em
# produção, apontaria pro serviço de verdade. O código não sabe a
# diferença, e esse é o ponto.
BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_CONNECT_TIMEOUT_SECONDS = float(
    os.environ.get("BANKSLIP_API_CONNECT_TIMEOUT_SECONDS", "1")
)
BANKSLIP_API_READ_TIMEOUT_SECONDS = float(
    os.environ.get("BANKSLIP_API_READ_TIMEOUT_SECONDS", "5")
)

# A API do Banco Central (consulta a índices como IPCA e IGPM)
CENTRAL_BANK_API_URL = os.environ.get("CENTRAL_BANK_API_URL", "http://mock:1080")
CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS = float(
    os.environ.get("CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS", "1")
)
CENTRAL_BANK_API_READ_TIMEOUT_SECONDS = float(
    os.environ.get("CENTRAL_BANK_API_READ_TIMEOUT_SECONDS", "5")
)

# Limites de cada transação PostgreSQL e orçamento total para pontos de espera
# conhecidos na requisição. Não há cancelamento cego de thread HTTP: depois de
# um cliente desistir, a mesma Idempotency-Key é a única repetição segura.
DATABASE_LOCK_TIMEOUT_MS = int(os.environ.get("DATABASE_LOCK_TIMEOUT_MS", "2000"))
DATABASE_STATEMENT_TIMEOUT_MS = int(os.environ.get("DATABASE_STATEMENT_TIMEOUT_MS", "10000"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS = int(
    os.environ.get("DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS", "2")
)
DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS = int(
    os.environ.get("DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS", "25")
)

# A outbox e o worker de notificações ficam fora do controller: o commit do
# domínio nunca depende de uma resposta de webhook. O destino padrão serve ao
# ambiente Compose; produção deve apontar para o serviço de notificações.
NOTIFICATION_WEBHOOK_URL = os.environ.get("NOTIFICATION_WEBHOOK_URL", "http://mock:1080/notifications")
OUTBOX_POLL_INTERVAL_SECONDS = float(os.environ.get("OUTBOX_POLL_INTERVAL_SECONDS", "1"))
OUTBOX_LEASE_SECONDS = int(os.environ.get("OUTBOX_LEASE_SECONDS", "30"))
OUTBOX_RETRY_BASE_SECONDS = int(os.environ.get("OUTBOX_RETRY_BASE_SECONDS", "5"))

# Regras e parâmetros de negócio (D1 e D8)
TRANSFER_FEE_CENTS = int(os.environ.get("TRANSFER_FEE_CENTS", "100"))
ADVANCE_FEE_PERCENT = int(os.environ.get("ADVANCE_FEE_PERCENT", "3"))
NIGHT_START = os.environ.get("NIGHT_START", "20:00")
NIGHT_END = os.environ.get("NIGHT_END", "06:00")
NIGHT_LIMIT_CENTS = int(os.environ.get("NIGHT_LIMIT_CENTS", "100000"))
TIMEZONE = os.environ.get("TIMEZONE", "America/Sao_Paulo")
# Configuração exclusiva do ambiente de teste: quando preenchida, substitui
# apenas a hora do relógio para tornar testes de janela noturna determinísticos.
NIGHT_TIME_OVERRIDE = os.environ.get("NIGHT_TIME_OVERRIDE") or None

# Rotas públicas: não exigem o header INTERNAL-TOKEN. São as duas que
# precisam responder pra quem ainda não tem token nenhum: a raiz, que
# diz quem é este serviço, e o health check, que o Docker consulta pra
# saber se a API já está de pé.
BYPASS_ENDPOINTS = [
    "/",
    "/health_check",
]

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN", "JWT_SECRET"]


def check_variables():
    missing = []
    for name in REQUIRED_VARIABLES:
        if not globals().get(name):
            missing.append(name)

    if missing:
        raise EnvironmentError(
            f"Faltam variáveis de ambiente: {', '.join(missing)}. "
            "Rodando com 'docker compose up' elas já vêm preenchidas. "
            "Fora do Docker, copie o .env.example para .env."
        )

    if NIGHT_LIMIT_CENTS < 1:
        raise EnvironmentError("NIGHT_LIMIT_CENTS must be a positive integer amount in cents.")

    if JWT_ACCESS_TOKEN_MINUTES < 1 or JWT_SESSION_MAX_HOURS < 1:
        raise EnvironmentError("JWT token durations must be positive integers.")

    timeout_values = {
        "BANKSLIP_API_CONNECT_TIMEOUT_SECONDS": BANKSLIP_API_CONNECT_TIMEOUT_SECONDS,
        "BANKSLIP_API_READ_TIMEOUT_SECONDS": BANKSLIP_API_READ_TIMEOUT_SECONDS,
        "CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS": CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS,
        "CENTRAL_BANK_API_READ_TIMEOUT_SECONDS": CENTRAL_BANK_API_READ_TIMEOUT_SECONDS,
        "REQUEST_TIMEOUT_SECONDS": REQUEST_TIMEOUT_SECONDS,
    }
    if any(value <= 0 for value in timeout_values.values()):
        raise EnvironmentError("Connector and request timeouts must be positive.")
    if DATABASE_LOCK_TIMEOUT_MS < 1 or DATABASE_STATEMENT_TIMEOUT_MS < 1:
        raise EnvironmentError("Database timeouts must be positive milliseconds.")
    if DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS < 1 or DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS < 0:
        raise EnvironmentError("Transient database retry settings must be non-negative and valid.")
    if OUTBOX_POLL_INTERVAL_SECONDS <= 0 or OUTBOX_LEASE_SECONDS < 1 or OUTBOX_RETRY_BASE_SECONDS < 1:
        raise EnvironmentError("Outbox intervals and lease must be positive.")

    # Import tardio evita ciclo durante a leitura das constantes acima.
    from utils.night_limit import validate_night_configuration

    validate_night_configuration()
