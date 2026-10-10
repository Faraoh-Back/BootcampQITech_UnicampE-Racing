from os import environ
import requests

from tests.utils.requisition import ClientRequisition


class TestSmoke:
    """Testes de fumaça (smoke tests) para validar a integridade básica da infraestrutura."""

    def test_root_endpoint_returns_200(self):
        """Rota pública raiz deve responder 200 identificando o serviço."""
        response = ClientRequisition.send("GET", "/")
        assert response.response_status == 200

    def test_health_check_returns_204(self):
        """Healthcheck usado pelo Docker deve responder 204 No Content."""
        response = ClientRequisition.send("GET", "/health_check")
        assert response.response_status == 204

    def test_protected_route_without_token_returns_403(self):
        """Rota protegida sem header INTERNAL-TOKEN deve ser recusada com 403 QIT000002."""
        response = ClientRequisition.send("GET", "/sample_entities")
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_protected_route_with_wrong_token_returns_403(self):
        """Rota protegida com token incorreto deve ser recusada com 403 QIT000002."""
        response = ClientRequisition.send(
            "GET",
            "/sample_entities",
            headers={"INTERNAL-TOKEN": "token_invalido_12345"},
        )
        assert response.response_status == 403
        assert response.response_json["code"] == "QIT000002"

    def test_mockserver_is_up_and_responsive(self):
        """MockServer (Mock dos conectores externos) deve responder na porta 1080."""
        mock_port = environ.get("MOCK_PORT", "1080")
        mock_host = environ.get("SERVER_LOCALHOST", "0.0.0.0")
        url = f"http://{mock_host}:{mock_port}/mockserver/status"
        resp = requests.put(url, timeout=3)
        assert resp.status_code == 200
        data = resp.json()
        assert "ports" in data
        # A API administrativa informa a porta de escuta DENTRO do container
        # (--serverPort 1080 no Compose), não a porta publicada no host.
        # MOCK_PORT=11080 continua acessando o serviço interno na porta 1080.
        assert 1080 in data["ports"]
