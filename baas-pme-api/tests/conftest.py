import time
from pathlib import Path
from os import path, environ
import pytest
import requests

from tests.utils.requisition import ClientRequisition
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator

root = Path(__file__).resolve().parents[1]

if not environ.get("APP_ENV") or environ.get("APP_ENV") == "local":
    from dotenv import load_dotenv

    load_dotenv(path.join(str(root), ".env"))

    if environ.get("SERVER_LOCALHOST") is None:
        environ["SERVER_LOCALHOST"] = "0.0.0.0"


@pytest.fixture(scope="session", autouse=True)
def ensure_api_is_ready():
    """Garante que a API no Docker está respondendo antes de rodar os testes."""
    api_host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
    api_port = environ.get("API_PORT", "3000")
    url = f"http://{api_host}:{api_port}/health_check"

    max_retries = 30
    delay = 0.5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code in (200, 204):
                return
        except requests.RequestException:
            pass
        time.sleep(delay)

    pytest.fail(
        f"A API em {url} não respondeu após {max_retries * delay}s. "
        "Verifique se o container está de pé com 'docker compose up -d'."
    )


@pytest.fixture
def make_customer():
    """Fábrica de clientes PME para testes de integração."""
    def _create(name=None, email=None, document_number=None, is_cnpj=True):
        payload = PayloadGenerator.create_customer_payload(
            name=name, email=email, document_number=document_number, is_cnpj=is_cnpj
        )
        status, response = RequestGenerator.POST_customer(payload)
        return {"status": status, "payload": payload, "response": response}

    return _create


@pytest.fixture
def make_account(make_customer):
    """Fábrica de contas para testes de integração."""
    def _create(customer_key=None):
        if customer_key is None:
            c = make_customer()
            customer_key = c["response"].get("customer_key")

        payload = PayloadGenerator.create_account_payload(customer_key=customer_key)
        status, response = RequestGenerator.POST_account(payload)
        return {
            "status": status,
            "customer_key": customer_key,
            "payload": payload,
            "response": response,
        }

    return _create
