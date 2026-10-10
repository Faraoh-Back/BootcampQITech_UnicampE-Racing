from uuid import uuid4

from tests.utils.request_generator import RequestGenerator


def user_payload(customer_key, role="OWNER"):
    return {"customer_key": customer_key, "name": "Responsável",
            "email": f"user-{uuid4()}@example.com", "password": "secure-pass-123", "role": role}


def owner_headers(customer_key, role="OWNER"):
    user = user_payload(customer_key, role)
    assert RequestGenerator.POST_user(user)[0] == 201
    status, tokens = RequestGenerator.POST_auth_login(
        {"email": user["email"], "password": user["password"]}
    )
    assert status == 201
    return {"Authorization": f"Bearer {tokens['access_token']}"}
