"""User and session rows. Does not commit; the request session does.

`revoke_stolen_session` is the exception: the handler then returns 401, and
the request session rolls back on that error.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from core.database.models import User, UserProfile, UserSession


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_email_or_username(self, email: str, username: str) -> User | None:
        return (
            self.db.query(User)
            .filter((User.email == email) | (User.username == username))
            .first()
        )

    def find_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def find_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def find_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def add(self, row) -> None:
        self.db.add(row)
        self.db.flush()

    def refresh(self, row) -> None:
        self.db.refresh(row)

    def active_session(
        self, session_id: str, user_id: int, now: datetime
    ) -> UserSession | None:
        return (
            self.db.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active.is_(True),
                UserSession.expires_at > now,
            )
            .first()
        )

    def revoke_stolen_session(self, user_session: UserSession) -> None:
        user_session.is_active = False
        self.db.commit()

    def deactivate_session(self, user_id: int, session_id: str) -> None:
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.session_id == session_id,
        ).update({UserSession.is_active: False}, synchronize_session=False)

    def profile(self, user_id: int) -> UserProfile | None:
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def revoke_sessions(self, user_id: int, keep_session_id: str | None = None) -> None:
        query = self.db.query(UserSession).filter(
            UserSession.user_id == user_id, UserSession.is_active.is_(True)
        )
        if keep_session_id:
            query = query.filter(UserSession.session_id != keep_session_id)
        query.update({UserSession.is_active: False}, synchronize_session=False)

    def expire_sessions(self, user_id: int, when: datetime) -> None:
        self.db.query(UserSession).filter(UserSession.user_id == user_id).update(
            {UserSession.expires_at: when}
        )
