"""Autorização opcional de usuário sobre a fronteira interna já existente.

Chamadas de serviço autenticadas apenas por INTERNAL-TOKEN continuam sendo o
ator técnico confiável do BaaS. Quando uma chamada carrega Authorization,
ela passa obrigatoriamente pela autorização de usuário para a conta alvo.
"""

from fastapi import Request

from controllers import AuthController


def authorize_user_if_present(request: Request, account_key: str, roles: set[str]) -> None:
    if request.headers.get("Authorization") is not None:
        AuthController().authorize_account(
            account_key, request.headers.get("Authorization"), roles
        )
