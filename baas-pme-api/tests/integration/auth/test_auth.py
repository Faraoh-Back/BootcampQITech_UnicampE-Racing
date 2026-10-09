from uuid import uuid4

from tests.utils.request_generator import RequestGenerator


def _user_payload(customer_key: str, role: str = "OWNER", email: str | None = None) -> dict:
    return {
        "customer_key": customer_key,
        "name": "Responsável da PME",
        "email": email or f"user-{uuid4()}@example.com",
        "password": "senha-segura-123",
        "role": role,
    }


def _bearer(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


class TestAuthentication:
    def test_registers_user_without_exposing_password_and_rotates_refresh_token(self, make_customer):
        customer_key = make_customer()["response"]["customer_key"]
        payload = _user_payload(customer_key)

        status, user = RequestGenerator.POST_user(payload)
        assert status == 201
        assert set(user) == {"user_key", "customer_key", "role", "created_at"}
        assert user["customer_key"] == customer_key
        assert user["role"] == "OWNER"
        assert "password" not in user

        status, tokens = RequestGenerator.POST_auth_login(
            {"email": payload["email"], "password": payload["password"], "device_name": "notebook"}
        )
        assert status == 201
        assert set(tokens) == {
            "access_token", "refresh_token", "token_type", "expires_in", "session_key"
        }
        assert tokens["token_type"] == "Bearer"
        assert tokens["expires_in"] == 15 * 60

        status, rotated = RequestGenerator.POST_auth_refresh(
            {"refresh_token": tokens["refresh_token"]}
        )
        assert status == 201
        assert rotated["session_key"] == tokens["session_key"]
        assert rotated["refresh_token"] != tokens["refresh_token"]

        status, error = RequestGenerator.POST_auth_refresh(
            {"refresh_token": tokens["refresh_token"]}
        )
        assert status == 401
        assert error["code"] == "QIT001020"

    def test_two_sessions_are_independent_and_logout_revokes_only_one(self, make_customer, make_account):
        customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(customer_key)["response"]["account_key"]
        payload = _user_payload(customer_key)
        status, _ = RequestGenerator.POST_user(payload)
        assert status == 201

        status, first = RequestGenerator.POST_auth_login(
            {"email": payload["email"], "password": payload["password"], "device_name": "phone"}
        )
        assert status == 201
        status, second = RequestGenerator.POST_auth_login(
            {"email": payload["email"], "password": payload["password"], "device_name": "desktop"}
        )
        assert status == 201
        assert first["session_key"] != second["session_key"]

        status, account = RequestGenerator.GET_account(account_key, headers=_bearer(first["access_token"]))
        assert status == 200
        assert account["account_key"] == account_key

        status, _ = RequestGenerator.POST_auth_logout(headers=_bearer(first["access_token"]))
        assert status == 204
        status, error = RequestGenerator.GET_account(account_key, headers=_bearer(first["access_token"]))
        assert status == 401
        assert error["code"] == "QIT001020"

        status, account = RequestGenerator.GET_account(account_key, headers=_bearer(second["access_token"]))
        assert status == 200
        assert account["account_key"] == account_key

    def test_enforces_customer_roles_and_hides_account_from_other_users(self, make_customer, make_account):
        owner_customer_key = make_customer()["response"]["customer_key"]
        account_key = make_account(owner_customer_key)["response"]["account_key"]
        viewer_payload = _user_payload(owner_customer_key, role="VIEWER")
        status, _ = RequestGenerator.POST_user(viewer_payload)
        assert status == 201
        status, viewer_tokens = RequestGenerator.POST_auth_login(
            {"email": viewer_payload["email"], "password": viewer_payload["password"]}
        )
        assert status == 201

        status, account = RequestGenerator.GET_account(
            account_key, headers=_bearer(viewer_tokens["access_token"])
        )
        assert status == 200
        assert account["account_key"] == account_key
        status, error = RequestGenerator.POST_transaction(
            account_key,
            {"type": "DEPOSIT", "amount": 100},
            headers=_bearer(viewer_tokens["access_token"]),
        )
        assert status == 403
        assert error["code"] == "QIT001022"

        foreign_customer_key = make_customer()["response"]["customer_key"]
        foreign_payload = _user_payload(foreign_customer_key)
        status, _ = RequestGenerator.POST_user(foreign_payload)
        assert status == 201
        status, foreign_tokens = RequestGenerator.POST_auth_login(
            {"email": foreign_payload["email"], "password": foreign_payload["password"]}
        )
        assert status == 201
        status, error = RequestGenerator.GET_account(
            account_key, headers=_bearer(foreign_tokens["access_token"])
        )
        assert status == 403
        assert error["code"] == "QIT001022"

    def test_rejects_invalid_credentials_and_duplicate_user_email(self, make_customer):
        customer_key = make_customer()["response"]["customer_key"]
        payload = _user_payload(customer_key)
        status, _ = RequestGenerator.POST_user(payload)
        assert status == 201
        status, error = RequestGenerator.POST_user(payload)
        assert status == 409
        assert error["code"] == "QIT001023"

        status, error = RequestGenerator.POST_auth_login(
            {"email": payload["email"], "password": "senha-incorreta"}
        )
        assert status == 401
        assert error["code"] == "QIT001021"
