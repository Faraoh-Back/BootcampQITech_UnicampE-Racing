from datetime import datetime
from uuid import uuid4

from database import Context
from models import Account, Customer, User, UserCustomerAccess, UserSession


class UserRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_customer_by_key(self, customer_key: str) -> Customer | None:
        return self.session.query(Customer).filter(Customer.customer_key == customer_key).first()

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email).first()

    def get_user_by_key(self, user_key: str) -> User | None:
        return self.session.query(User).filter(User.user_key == user_key).first()

    def create_user(
        self, customer: Customer, name: str, email: str, password_hash: str, role: str
    ) -> User:
        user = User(user_key=str(uuid4()), name=name, email=email, password_hash=password_hash)
        self.session.add(user)
        self.session.flush()
        self.session.add(UserCustomerAccess(user=user, customer=customer, role=role))
        self.session.flush()
        return user

    def create_session(
        self, user: User, refresh_token_hash: str, expires_at: datetime, device_name: str | None
    ) -> UserSession:
        session = UserSession(
            session_key=str(uuid4()),
            user=user,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_name=device_name,
        )
        self.session.add(session)
        self.session.flush()
        return session

    def get_active_session_for_refresh(self, refresh_token_hash: str) -> UserSession | None:
        return (
            self.session.query(UserSession)
            .filter(
                UserSession.refresh_token_hash == refresh_token_hash,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.utcnow(),
            )
            .with_for_update()
            .first()
        )

    def get_active_session_by_key_for_user(
        self, session_key: str, user_key: str
    ) -> UserSession | None:
        return (
            self.session.query(UserSession)
            .join(User)
            .filter(
                UserSession.session_key == session_key,
                User.user_key == user_key,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.utcnow(),
            )
            .first()
        )

    def rotate_refresh_token(self, session: UserSession, refresh_token_hash: str) -> None:
        session.refresh_token_hash = refresh_token_hash

    def revoke_session(self, session: UserSession) -> None:
        session.revoked_at = datetime.utcnow()

    def count_active_sessions(self) -> int:
        return (
            self.session.query(UserSession)
            .filter(
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.utcnow(),
            )
            .count()
        )

    def get_account_role(self, user_id: int, account_key: str) -> str | None:
        access = (
            self.session.query(UserCustomerAccess)
            .join(Account, Account.customer_id == UserCustomerAccess.customer_id)
            .filter(UserCustomerAccess.user_id == user_id, Account.account_key == account_key)
            .first()
        )
        return access.role if access is not None else None

    def get_customer_role(self, user_id: int, customer_id: int) -> str | None:
        access = self.session.query(UserCustomerAccess).filter(
            UserCustomerAccess.user_id == user_id,
            UserCustomerAccess.customer_id == customer_id,
        ).first()
        return access.role if access is not None else None
