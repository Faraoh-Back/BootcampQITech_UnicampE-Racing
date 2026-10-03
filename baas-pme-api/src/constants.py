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

# A API de boletos: o serviço de fora que este projeto chama pra emitir
# uma cobrança (veja src/connectors/). O endereço vem do ambiente, como
# tudo aqui — na sua máquina ele aponta pro mock server do sábado 4; em
# produção, apontaria pro serviço de verdade. O código não sabe a
# diferença, e esse é o ponto.
BANKSLIP_API_URL = os.environ.get("BANKSLIP_API_URL", "http://localhost:8080")
BANKSLIP_API_TIMEOUT = int(os.environ.get("BANKSLIP_API_TIMEOUT", "5"))

# A API do Banco Central (consulta a índices como IPCA e IGPM)
CENTRAL_BANK_API_URL = os.environ.get("CENTRAL_BANK_API_URL", "http://mock:1080")
CENTRAL_BANK_API_TIMEOUT = int(os.environ.get("CENTRAL_BANK_API_TIMEOUT", "5"))

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

REQUIRED_VARIABLES = ["DATABASE_URL", "INTERNAL_TOKEN"]


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

    # Import tardio evita ciclo durante a leitura das constantes acima.
    from utils.night_limit import validate_night_configuration

    validate_night_configuration()
