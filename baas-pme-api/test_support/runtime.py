"""Orquestra containers descartáveis; sem imports, SQL ou alterações em src/."""

from contextlib import contextmanager
from datetime import datetime, time as clock_time, timezone
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

import requests


PROJECT = Path(__file__).resolve().parents[1]

# Também usados pelo worker executado no host nos contratos de infraestrutura.
# Configuração financeira real do desenvolvedor nunca governa o perfil gerido.
TEST_APPLICATION_ENVIRONMENT = {
    "APP_ENV": "local", "INTERNAL_TOKEN": "default_token",
    "JWT_SECRET": "isolated-test-jwt-secret-not-for-production",
    "JWT_ACCESS_TOKEN_MINUTES": "15", "JWT_SESSION_MAX_HOURS": "8",
    "NIGHT_START": "20:00", "NIGHT_END": "06:00", "NIGHT_LIMIT_CENTS": "100000",
    "TIMEZONE": "America/Sao_Paulo", "NIGHT_TIME_OVERRIDE": "21:00",
    "BANKSLIP_API_CONNECT_TIMEOUT_SECONDS": "1", "BANKSLIP_API_READ_TIMEOUT_SECONDS": "5",
    "CENTRAL_BANK_API_CONNECT_TIMEOUT_SECONDS": "1", "CENTRAL_BANK_API_READ_TIMEOUT_SECONDS": "5",
    "DATABASE_LOCK_TIMEOUT_MS": "2000", "DATABASE_STATEMENT_TIMEOUT_MS": "10000",
    "REQUEST_TIMEOUT_SECONDS": "15", "DATABASE_TRANSIENT_RETRY_MAX_ATTEMPTS": "2",
    "DATABASE_TRANSIENT_RETRY_BASE_DELAY_MS": "25", "OUTBOX_POLL_INTERVAL_SECONDS": "1",
    "OUTBOX_LEASE_SECONDS": "30", "OUTBOX_RETRY_BASE_SECONDS": "5",
}


class TestEnvironmentError(RuntimeError):
    __test__ = False


class TestRuntime:
    __test__ = False

    def __init__(self, internal_token="default_token"):
        self.project = f"baas-pytest-{uuid4().hex}"
        self.compose_file = PROJECT / "docker-compose.test.yml"
        self.environment = os.environ.copy()
        for key in ("COMPOSE_PROFILES", "COMPOSE_PROJECT_NAME", "COMPOSE_FILE"):
            self.environment.pop(key, None)
        self.environment["BAAS_TEST_INTERNAL_TOKEN"] = internal_token
        self.environment["BAAS_TEST_API_IMAGE"] = f"{self.project}-api"
        self.client_environment = {}
        self.started = False
        self.closed = False
        self.clock_port = None
        self.clock_time = None
        self.report_directory = PROJECT / "artifacts" / "test-runs" / self.project
        self.started_at = None

    def _compose(self, *arguments, timeout=180):
        command = [
            "docker", "compose", "--project-name", self.project,
            "--file", str(self.compose_file), "--profile", "clock", *arguments,
        ]
        try:
            result = subprocess.run(
                command, cwd=PROJECT, env=self.environment, capture_output=True,
                text=True, timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise TestEnvironmentError(
                f"Infraestrutura de testes: Docker indisponível ou comando expirou ({self.project}). "
                "Confira Docker Engine/Compose e a permissão no socket."
            ) from error
        if result.returncode:
            # Saída do Compose pode conter configuração sensível. Não imprimir
            # ambiente, logs ou credenciais indiscriminadamente no relatório.
            raise TestEnvironmentError(
                f"Infraestrutura de testes: docker compose {' '.join(arguments)} falhou "
                f"(status {result.returncode}, projeto {self.project}). "
                "Confira Docker, imagens/dependências e espaço em disco."
            )
        return result.stdout.strip()

    def _port(self, service, internal_port):
        mapping = self._compose("port", service, str(internal_port))
        try:
            host, port = mapping.rsplit(":", 1)
            port = int(port)
            if host != "127.0.0.1" or not 1 <= port <= 65535:
                raise ValueError
        except ValueError as error:
            raise TestEnvironmentError(f"Porta de teste inválida para {service}.") from error
        return str(port)

    def _wait_http(self, port, path, *, method="GET", status=204, timeout=90):
        deadline = time.monotonic() + timeout
        url = f"http://127.0.0.1:{port}{path}"
        while time.monotonic() < deadline:
            try:
                response = requests.request(method, url, timeout=2)
                if response.status_code == status:
                    return
            except requests.RequestException:
                pass
            time.sleep(0.25)
        raise TestEnvironmentError(f"Serviço de teste não ficou pronto: {path} ({self.project}).")

    def start(self):
        if self.closed:
            raise TestEnvironmentError("Não é permitido reutilizar um ambiente já encerrado.")
        if self.started:
            return self
        # Resolve a imagem antes de construir: api-clock usa a mesma imagem,
        # sem build/reload a cada mudança de hora.
        self._compose("config", "--quiet")
        self.started = True  # inclui recursos parcialmente criados em falhas
        self.started_at = datetime.now(timezone.utc).isoformat()
        try:
            self._compose("up", "--detach", "--build", "api", "db", "mock", timeout=600)
            api_port = self._port("api", 3000)
            db_port = self._port("db", 5432)
            mock_port = self._port("mock", 1080)
            self.client_environment = {
                **TEST_APPLICATION_ENVIRONMENT,
                "INTERNAL_TOKEN": self.environment["BAAS_TEST_INTERNAL_TOKEN"],
                "SERVER_LOCALHOST": "127.0.0.1", "API_PORT": api_port,
                "MOCK_HOST": "127.0.0.1", "MOCK_PORT": mock_port,
                "DATABASE_URL": f"postgresql+psycopg2://bootcamp:bootcamp@127.0.0.1:{db_port}/bootcamp",
            }
            self._wait_http(api_port, "/health_check")
            self._wait_http(mock_port, "/mockserver/reset", method="PUT", status=200)
        except BaseException:
            self.close()
            raise
        return self

    @contextmanager
    def clock(self, value):
        try:
            clock_time.fromisoformat(value)
        except (ValueError, TypeError) as error:
            raise TestEnvironmentError("Hora de teste inválida; use HH:MM.") from error
        self.start()
        if self.clock_time != value:
            self.environment["BAAS_TEST_CLOCK_TIME"] = value
            self._compose("up", "--detach", "--no-deps", "--no-build", "api-clock")
            self.clock_port = self._port("api-clock", 3000)
            self._wait_http(self.clock_port, "/health_check")
            self.clock_time = value
        # Muda o DESTINO HTTP do cliente, não o relógio por HTTP. A aplicação
        # recebe o horário exclusivamente na criação do container api-clock.
        values = {**self.client_environment, "API_PORT": self.clock_port}
        previous = {key: os.environ.get(key) for key in values}
        os.environ.update(values)
        try:
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def _capture_evidence(self):
        if not self.client_environment:
            return None
        self.report_directory.mkdir(parents=True, exist_ok=True)
        report = {
            "compose_project": self.project, "compose_file": self.compose_file.name,
            "started_at_utc": self.started_at, "main_clock": "21:00",
            "last_boundary_clock": self.clock_time,
            "ports": {key: value for key, value in self.client_environment.items() if key.endswith("PORT")},
            "cleanup": "pending", "metrics": {},
        }
        for service, port in (("api", self.client_environment["API_PORT"]),
                              ("api-clock", self.clock_port)):
            if port is None:
                continue
            try:
                response = requests.get(f"http://127.0.0.1:{port}/metrics",
                    headers={"INTERNAL-TOKEN": self.environment["BAAS_TEST_INTERNAL_TOKEN"]}, timeout=3)
                response.raise_for_status()
                (self.report_directory / f"{service}-metrics.prom").write_text(response.text)
                report["metrics"][service] = "captured"
            except requests.RequestException:
                report["metrics"][service] = "unavailable"
        return report

    def close(self):
        if self.closed or not self.started:
            return
        # Falha ao gravar evidência (por exemplo disco cheio) não pode impedir
        # a tentativa de remover o ambiente descartável.
        report = None
        try:
            report = self._capture_evidence()
        finally:
            # Alvo é o UUID gerado aqui, nunca o projeto de desenvolvimento.
            try:
                self._compose("down", "--volumes", "--remove-orphans", timeout=120)
                if self._compose("ps", "--all", "--quiet"):
                    raise TestEnvironmentError(
                        f"Falha no cleanup: restaram containers em {self.project}."
                    )
                self.closed = True
            finally:
                if report is not None:
                    report["cleanup"] = "removed" if self.closed else "failed"
                    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                    (self.report_directory / "environment.json").write_text(json.dumps(report, indent=2) + "\n")
