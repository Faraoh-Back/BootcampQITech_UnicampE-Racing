"""Funcoes para configurar o MockServer nos testes de integracao.

O MockServer e tratado como um servico externo: os testes o configuram pela
API administrativa e a aplicacao continua falando apenas com as URLs dos
conectores. Nenhuma funcao deste modulo importa codigo de ``src/`` (R1).
"""

import json
from os import environ
from typing import Iterable

import requests


_ADMIN_TIMEOUT_SECONDS = 3


def _base_url() -> str:
    host = environ.get("MOCK_HOST", environ.get("SERVER_LOCALHOST", "0.0.0.0"))
    port = environ.get("MOCK_PORT", "1080")
    return f"http://{host}:{port}"


def _admin_request(endpoint: str, payload: dict | None = None) -> requests.Response:
    try:
        response = requests.put(
            f"{_base_url()}{endpoint}", json=payload, timeout=_ADMIN_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response
    except requests.HTTPError as error:
        raise RuntimeError(
            f"O MockServer rejeitou a configuracao em {endpoint}: "
            f"{error.response.status_code} {error.response.text}"
        ) from error
    except requests.RequestException as error:
        raise RuntimeError(
            f"Nao foi possivel configurar o MockServer em {_base_url()}. "
            "Suba o ambiente com 'docker compose up'."
        ) from error


def _expect(request: dict, response: dict, delay_seconds: int | None = None) -> None:
    expectation_response = response.copy()
    if delay_seconds is not None:
        expectation_response["delay"] = {"timeUnit": "SECONDS", "value": delay_seconds}
    expectation = {"httpRequest": request, "httpResponse": expectation_response}
    _admin_request("/mockserver/expectation", expectation)


def _json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": ["application/json"]},
        "body": json.dumps(body),
    }


def reset() -> None:
    """Remove todas as expectativas e registros de chamadas do MockServer."""
    _admin_request("/mockserver/reset")


def expect_bankslip_ok(installment_numbers: Iterable[int] = range(1, 13)) -> None:
    """Configura uma emissao de boletos bem-sucedida.

    ``installment_numbers`` permite usar o mesmo helper para o lote inicial
    (1 a 12) e para o lote de reajuste (13 a 24).
    """
    bank_slips = [
        {
            "installment_number": installment_number,
            "barcode": f"MOCK-BARCODE-{installment_number:02d}",
        }
        for installment_number in installment_numbers
    ]
    _expect(
        {"method": "POST", "path": "/bank-slips"},
        _json_response(200, {"bank_slips": bank_slips}),
    )


def expect_bankslip_timeout() -> None:
    """Configura atraso acima dos 5 segundos do conector de boletos."""
    _expect(
        {"method": "POST", "path": "/bank-slips"},
        _json_response(200, {"bank_slips": []}),
        delay_seconds=6,
    )


def expect_bankslip_status(status_code: int) -> None:
    """Configura uma resposta HTTP de falha para a emissao de boletos."""
    _expect(
        {"method": "POST", "path": "/bank-slips"},
        _json_response(status_code, {"error": "mocked bank-slip failure"}),
    )


def expect_bankslip_invalid_json() -> None:
    """Configura uma resposta 200 cujo corpo nao pode ser interpretado como JSON."""
    _expect(
        {"method": "POST", "path": "/bank-slips"},
        {
            "statusCode": 200,
            "headers": {"Content-Type": ["text/plain"]},
            "body": "not-json",
        },
    )


def expect_bankslip_missing_barcode() -> None:
    """Configura uma resposta 200 sem o campo obrigatório ``barcode``."""
    _expect(
        {"method": "POST", "path": "/bank-slips"},
        _json_response(200, {"bank_slips": [{"installment_number": 1}]}),
    )


def expect_central_bank_rate(index: str, rate: str) -> None:
    """Configura a taxa acumulada para um indice, por exemplo IPCA ou IGPM."""
    _expect(
        {"method": "GET", "path": f"/index/{index}"},
        _json_response(200, {"index": index, "accumulated_rate": rate}),
    )


def expect_central_bank_status(status_code: int) -> None:
    """Configura uma resposta HTTP de falha para qualquer consulta de indice."""
    _expect(
        {"method": "GET", "path": "/index/.*", "pathParameters": {}},
        _json_response(status_code, {"error": "mocked central-bank failure"}),
    )


def verify_called(path: str, times: int) -> None:
    """Falha o teste se ``path`` nao tiver sido chamado exatamente ``times`` vezes."""
    payload = {
        "httpRequest": {"path": path},
        "times": {"atLeast": times, "atMost": times},
    }
    try:
        response = requests.put(f"{_base_url()}/mockserver/verify", json=payload, timeout=_ADMIN_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        raise RuntimeError(f"Nao foi possivel verificar o MockServer em {_base_url()}.") from error

    if response.status_code != 202:
        raise AssertionError(
            f"Esperava {times} chamada(s) para {path}, mas o MockServer respondeu "
            f"{response.status_code}: {response.text}"
        )


def verify_bankslip_external_reference(external_reference: str) -> None:
    """Confere o contrato da referência enviada ao emissor de boletos."""
    try:
        response = requests.put(
            f"{_base_url()}/mockserver/retrieve?type=REQUESTS",
            json={"method": "POST", "path": "/bank-slips"},
            timeout=_ADMIN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Nao foi possivel recuperar chamadas do MockServer em {_base_url()}.") from error

    requests_made = response.json()
    if not requests_made:
        raise AssertionError("O MockServer não registrou uma chamada para /bank-slips.")

    body = requests_made[-1].get("body")
    if isinstance(body, dict):
        body = body.get("string", body.get("json", body))
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or body.get("external_reference") != external_reference:
        raise AssertionError(
            "A external_reference enviada ao MockServer é diferente da referência esperada."
        )
