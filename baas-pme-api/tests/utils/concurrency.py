"""Utilitários para testes de corrida HTTP sem compartilhar cliente entre threads."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Callable, TypeVar

import requests


Result = TypeVar("Result")


def run_parallel(
    workers: int, fn: Callable[[requests.Session], Result], timeout_seconds: int = 15
) -> list[Result]:
    """Dispara ``workers`` chamadas ao mesmo tempo, cada uma com sua sessão.

    A barreira é alcançada antes de a função receber a sessão. Assim nenhuma
    chamada HTTP começa antes de todas as threads estarem prontas; os testes
    exercitam a disputa pela mesma trava no PostgreSQL de verdade.
    """
    barrier = Barrier(workers, timeout=timeout_seconds)

    def execute() -> Result:
        with requests.Session() as session:
            barrier.wait()
            return fn(session)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(execute) for _ in range(workers)]
        return [future.result(timeout=timeout_seconds) for future in futures]
