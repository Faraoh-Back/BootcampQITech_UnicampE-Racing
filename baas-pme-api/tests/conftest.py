import time
from pathlib import Path
from os import path, environ
import pytest
import requests

root = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(items):
    """Mantém as evidências HTTP, de infraestrutura e estáticas distinguíveis.

    A execução completa continua sendo pytest tests. Os contratos que
    controlam PostgreSQL/worker são úteis, mas não são prova HTTP da R1.
    """
    infrastructure_modules = {
        "tests/integration/timeouts/test_timeouts.py",
        "tests/integration/transaction/test_transient_retry.py",
        "tests/integration/outbox/test_outbox.py",
        "tests/integration/sample_entity/test_sample_entities.py",
        "tests/integration/credit_advance/test_positive_net_database.py",
    }
    for item in items:
        relative = Path(str(item.fspath)).relative_to(root).as_posix()
        if "/sample_entity/" in relative:
            item.add_marker(pytest.mark.legacy)
        if relative in {"tests/test_r1_guard.py", "tests/test_documentation_contract.py",
                        "tests/test_test_environment.py"}:
            item.add_marker(pytest.mark.static_guard)
        elif relative in infrastructure_modules or (
            relative == "tests/integration/audit/test_audit.py"
            and item.originalname == "test_database_rejects_update_and_delete_of_audit_events"
        ):
            item.add_marker(pytest.mark.infrastructure_contract)
        else:
            item.add_marker(pytest.mark.api_blackbox)

if not environ.get("APP_ENV") or environ.get("APP_ENV") == "local":
    from dotenv import load_dotenv

    load_dotenv(path.join(str(root), ".env"))

    if environ.get("SERVER_LOCALHOST") is None:
        environ["SERVER_LOCALHOST"] = "0.0.0.0"


def pytest_addoption(parser):
    parser.addoption(
        "--test-environment", choices=("managed", "external"), default="managed",
        help="managed inicia Compose descartável automaticamente; external usa infraestrutura já preparada",
    )


def pytest_configure(config):
    if getattr(config.option, "numprocesses", None):
        raise pytest.UsageError("A suíte usa execução sequencial: remova -n/pytest-xdist.")
    # Executa antes da coleta/importação dos helpers que capturam o token.
    # .env local, URLs externas e relógio do host não governam o perfil gerido.
    patch = pytest.MonkeyPatch()
    config._test_environment_patch = patch
    if config.getoption("test_environment") == "managed":
        from test_support.runtime import TEST_APPLICATION_ENVIRONMENT
        for key, value in TEST_APPLICATION_ENVIRONMENT.items():
            patch.setenv(key, value)


def pytest_unconfigure(config):
    patch = getattr(config, "_test_environment_patch", None)
    if patch is not None:
        patch.undo()


@pytest.fixture(scope="session")
def test_runtime(request):
    if request.config.getoption("test_environment") == "external":
        yield None
        return
    from test_support.runtime import TestRuntime

    runtime = TestRuntime()
    patch = pytest.MonkeyPatch()
    try:
        runtime.start()
        for key, value in runtime.client_environment.items():
            patch.setenv(key, value)
        reporter = request.config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            reporter.write_line(f"Ambiente descartável: {runtime.project}; relógio principal 21:00")
        yield runtime
    finally:
        patch.undo()
        runtime.close()


@pytest.fixture(scope="session")
def clock_runtime(request):
    runtime = request.getfixturevalue("test_runtime")
    if runtime is not None:
        yield runtime
        return
    # Até no modo externo os cenários de fronteira têm containers próprios;
    # não reconfiguramos o servidor/banco fornecidos pelo operador.
    from test_support.runtime import TestRuntime

    runtime = TestRuntime(internal_token=environ.get("INTERNAL_TOKEN", "default_token"))
    try:
        runtime.start()
        yield runtime
    finally:
        runtime.close()


@pytest.fixture
def api_at_time(clock_runtime):
    return clock_runtime.clock


@pytest.fixture(scope="session", autouse=True)
def ensure_api_is_ready(request):
    """Garante que a API no Docker está respondendo antes de rodar os testes."""
    if all(item.get_closest_marker("static_guard") for item in request.session.items):
        return
    request.getfixturevalue("test_runtime")
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
        "No modo external, confira a infraestrutura previamente preparada."
    )


@pytest.fixture
def make_customer():
    """Fábrica de clientes PME para testes de integração."""
    from tests.utils.payload_generator import PayloadGenerator
    from tests.utils.request_generator import RequestGenerator
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
    from tests.utils.payload_generator import PayloadGenerator
    from tests.utils.request_generator import RequestGenerator
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
