"""Contratos do bootstrap de infraestrutura; não são provas HTTP do produto."""

from pathlib import Path
import os
import subprocess
from types import SimpleNamespace

import pytest

from test_support.runtime import TestEnvironmentError, TestRuntime


PROJECT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.static_guard


def test_test_compose_is_separate_and_has_fixed_clocks():
    compose = PROJECT / "docker-compose.test.yml"
    assert compose.exists(), "pytest precisa de infraestrutura própria, não do Compose de desenvolvimento"
    configuration = compose.read_text()
    assert 'NIGHT_TIME_OVERRIDE: "21:00"' in configuration
    assert "api-clock:" in configuration
    assert "127.0.0.1::3000" in configuration
    assert "./src:/app" not in configuration


def test_runtime_never_uses_the_development_project_or_ports(monkeypatch):
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "baas-pme-api")
    monkeypatch.setenv("COMPOSE_FILE", "docker-compose.yml")
    monkeypatch.setenv("COMPOSE_PROFILES", "workers")
    monkeypatch.setenv("API_PORT", "3000")
    first, second = TestRuntime(), TestRuntime()
    assert first.project.startswith("baas-pytest-")
    assert first.project != second.project
    assert first.compose_file.name == "docker-compose.test.yml"
    assert "COMPOSE_PROFILES" not in first.environment
    assert first.environment["BAAS_TEST_API_IMAGE"] == f"{first.project}-api"


def test_docker_commands_are_explicitly_scoped_and_never_use_a_shell(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    runtime = TestRuntime()
    runtime.started = True
    runtime.close()
    runtime.close()
    assert len(calls) == 2
    command, options = calls[0]
    assert command == ["docker", "compose", "--project-name", runtime.project,
        "--file", str(runtime.compose_file), "--profile", "clock", "down", "--volumes", "--remove-orphans"]
    assert calls[1][0][-4:] == ["clock", "ps", "--all", "--quiet"]
    assert not options.get("shell")
    assert runtime.closed


@pytest.mark.parametrize("mapping", ["0.0.0.0:3000", "127.0.0.1:0", "bad", "127.0.0.1:65536"])
def test_invalid_or_public_port_mapping_is_rejected(monkeypatch, mapping):
    runtime = TestRuntime()
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs: mapping)
    with pytest.raises(TestEnvironmentError, match="Porta de teste inválida"):
        runtime._port("api", 3000)


def test_docker_failure_does_not_leak_output_or_secrets(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs:
        SimpleNamespace(returncode=1, stdout="private-test-secret", stderr="private-test-secret"))
    with pytest.raises(TestEnvironmentError) as error:
        TestRuntime()._compose("config", "--quiet")
    assert "private-test-secret" not in str(error.value)


def test_partial_startup_failure_cleans_up_its_own_project(monkeypatch):
    runtime = TestRuntime()
    calls = []

    def compose(*args, **kwargs):
        calls.append(args)
        if args[0] == "up":
            raise TestEnvironmentError("synthetic startup failure")
        return ""

    monkeypatch.setattr(runtime, "_compose", compose)
    with pytest.raises(TestEnvironmentError, match="synthetic startup"):
        runtime.start()
    assert calls[-2:] == [("down", "--volumes", "--remove-orphans"), ("ps", "--all", "--quiet")]
    assert runtime.closed


def test_clock_fixture_restores_client_environment_even_when_assertion_fails(monkeypatch):
    runtime = TestRuntime()
    runtime.started = True
    runtime.client_environment = {"API_PORT": "49100", "MOCK_PORT": "49101"}
    monkeypatch.setenv("API_PORT", "3000")
    monkeypatch.delenv("MOCK_PORT", raising=False)
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs: "")
    monkeypatch.setattr(runtime, "_port", lambda *args: "49102")
    monkeypatch.setattr(runtime, "_wait_http", lambda *args, **kwargs: None)
    with pytest.raises(AssertionError, match="synthetic assertion"):
        with runtime.clock("20:00"):
            assert os.environ["API_PORT"] == "49102"
            assert os.environ["MOCK_PORT"] == "49101"
            assert runtime.environment["BAAS_TEST_CLOCK_TIME"] == "20:00"
            raise AssertionError("synthetic assertion")
    assert os.environ["API_PORT"] == "3000"
    assert "MOCK_PORT" not in os.environ


def test_invalid_clock_fails_before_any_docker_command(monkeypatch):
    runtime = TestRuntime()
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs: pytest.fail("Docker não deve ser chamado"))
    with pytest.raises(TestEnvironmentError, match="Hora de teste inválida"):
        with runtime.clock("25:00"):
            pass


def test_docker_socket_or_binary_failure_has_actionable_error(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("synthetic missing docker")
    monkeypatch.setattr(subprocess, "run", unavailable)
    with pytest.raises(TestEnvironmentError, match="permissão no socket"):
        TestRuntime()._compose("config", "--quiet")


def test_evidence_write_failure_does_not_prevent_cleanup(monkeypatch):
    runtime = TestRuntime()
    runtime.started = True
    calls = []
    def cannot_save():
        raise OSError("synthetic disk full")
    monkeypatch.setattr(runtime, "_capture_evidence", cannot_save)
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(OSError, match="synthetic disk full"):
        runtime.close()
    assert calls == [("down", "--volumes", "--remove-orphans"), ("ps", "--all", "--quiet")]
    assert runtime.closed


def test_an_already_closed_runtime_cannot_start_again(monkeypatch):
    runtime = TestRuntime()
    runtime.started = True
    runtime.closed = True
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs: pytest.fail("Docker não deve ser chamado"))
    with pytest.raises(TestEnvironmentError, match="já encerrado"):
        runtime.start()


def test_cleanup_must_not_report_success_when_a_profile_container_remains(monkeypatch):
    runtime = TestRuntime()
    runtime.started = True
    monkeypatch.setattr(runtime, "_compose", lambda *args, **kwargs:
        "clock-container-still-present" if args[0] == "ps" else "")
    with pytest.raises(TestEnvironmentError, match="restaram containers"):
        runtime.close()
    assert not runtime.closed
