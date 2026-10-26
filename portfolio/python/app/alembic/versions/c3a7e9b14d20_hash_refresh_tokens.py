"""Hash refresh tokens already stored on user sessions.

New sessions are hashed by the application. This revision hashes rows that
still hold the token itself, so an existing login keeps working. A SHA-256
hex digest is 64 characters; those rows are left as they are.

Downgrade cannot restore the tokens.

Revision ID: c3a7e9b14d20
Revises: b8c1d4e27a90
Create Date: 2026-10-26

"""

import hashlib

import sqlalchemy as sa

from alembic import op

revision = "c3a7e9b14d20"
down_revision = "b8c1d4e27a90"
branch_labels = None
depends_on = None


def _digest(token: str) -> str:
    # Same digest as core.auth.utils.hash_refresh_token.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, refresh_token FROM user_sessions")
    ).fetchall()
    for row in rows:
        token = row.refresh_token
        if token is None or (
            len(token) == 64 and all(c in "0123456789abcdef" for c in token)
        ):
            continue
        bind.execute(
            sa.text("UPDATE user_sessions SET refresh_token = :digest WHERE id = :id"),
            {"digest": _digest(token), "id": row.id},
        )


def downgrade() -> None:
    pass
