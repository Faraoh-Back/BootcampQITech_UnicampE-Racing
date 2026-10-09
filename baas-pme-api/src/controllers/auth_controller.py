from datetime import datetime, timedelta

from controllers.base_controller import BaseController
from dtos import UserDTO
from errors import (
    AccountAccessForbidden,
    CustomerNotFound,
    DuplicatedUserEmail,
    InvalidAccessToken,
    InvalidCredentials,
)
from repositories import UserRepository
from utils.authentication import (
    bearer_token,
    decode_access_token,
    hash_password,
    issue_access_token,
    new_refresh_token,
    password_matches,
    refresh_token_hash,
)
from constants import JWT_ACCESS_TOKEN_MINUTES, JWT_SESSION_MAX_HOURS


class AuthController(BaseController):
    """Identidade de usuário sem misturar a fronteira do INTERNAL-TOKEN."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.user_repository = UserRepository(self.context)

    def register(self, payload: dict) -> dict:
        customer = self.user_repository.get_customer_by_key(payload["customer_key"])
        if customer is None:
            raise CustomerNotFound(payload["customer_key"])
        if self.user_repository.get_user_by_email(payload["email"]) is not None:
            raise DuplicatedUserEmail()

        role = payload.get("role", "OWNER")
        user = self.user_repository.create_user(
            customer,
            payload["name"],
            payload["email"],
            hash_password(payload["password"]),
            role,
        )
        response = UserDTO.obj_to_created_dict(user, customer.customer_key, role)
        self.session.commit()
        return response

    def login(self, payload: dict) -> dict:
        user = self.user_repository.get_user_by_email(payload["email"])
        if user is None or not password_matches(payload["password"], user.password_hash):
            raise InvalidCredentials()

        response = self._create_session_response(user, payload.get("device_name"))
        self.session.commit()
        return response

    def refresh(self, refresh_token: str) -> dict:
        session = self.user_repository.get_active_session_for_refresh(refresh_token_hash(refresh_token))
        if session is None:
            raise InvalidAccessToken()

        next_refresh_token = new_refresh_token()
        self.user_repository.rotate_refresh_token(session, refresh_token_hash(next_refresh_token))
        response = self._token_response(session.user.user_key, session.session_key, next_refresh_token)
        self.session.commit()
        return response

    def logout(self, authorization: str | None) -> None:
        claims = self._claims_for_active_session(authorization)
        session = self.user_repository.get_active_session_by_key_for_user(claims["sid"], claims["sub"])
        if session is None:
            raise InvalidAccessToken()
        self.user_repository.revoke_session(session)
        self.session.commit()

    def authorize_account(
        self, account_key: str, authorization: str | None, allowed_roles: set[str]
    ) -> None:
        claims = self._claims_for_active_session(authorization)
        session = self.user_repository.get_active_session_by_key_for_user(claims["sid"], claims["sub"])
        if session is None:
            raise InvalidAccessToken()
        role = self.user_repository.get_account_role(session.user_id, account_key)
        if role not in allowed_roles:
            raise AccountAccessForbidden()

    def _claims_for_active_session(self, authorization: str | None) -> dict:
        try:
            token = bearer_token(authorization)
            if token is None:
                raise ValueError("missing authorization header")
            return decode_access_token(token)
        except (KeyError, ValueError):
            raise InvalidAccessToken() from None

    def _create_session_response(self, user, device_name: str | None) -> dict:
        refresh_token = new_refresh_token()
        expires_at = datetime.utcnow() + timedelta(hours=JWT_SESSION_MAX_HOURS)
        session = self.user_repository.create_session(
            user, refresh_token_hash(refresh_token), expires_at, device_name
        )
        return self._token_response(user.user_key, session.session_key, refresh_token)

    @staticmethod
    def _token_response(user_key: str, session_key: str, refresh_token: str) -> dict:
        return {
            "access_token": issue_access_token(user_key, session_key),
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": JWT_ACCESS_TOKEN_MINUTES * 60,
            "session_key": session_key,
        }
