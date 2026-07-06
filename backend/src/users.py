from __future__ import annotations

import hashlib

from .database import get_connection
from .models import AuthUserSyncRequest, UserRecord


def _user_id(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:32]


def sync_user(payload: AuthUserSyncRequest) -> UserRecord:
    email = payload.email.strip().lower()
    user_id = _user_id(email)
    provider = payload.provider or "google"
    provider_account_id = payload.provider_account_id or email
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, name, image, role, created_at, updated_at, last_login_at)
                VALUES (%s, %s, %s, %s, %s, now(), now(), now())
                ON CONFLICT (email) DO UPDATE SET
                    name = EXCLUDED.name,
                    image = EXCLUDED.image,
                    role = EXCLUDED.role,
                    updated_at = now(),
                    last_login_at = now()
                RETURNING id, email, name, image, role,
                    created_at::text AS created_at,
                    updated_at::text AS updated_at,
                    last_login_at::text AS last_login_at
                """,
                (user_id, email, payload.name, payload.image, payload.role),
            )
            row = cur.fetchone()
            stored_user_id = row["id"]
            cur.execute(
                """
                INSERT INTO user_accounts (id, user_id, provider, provider_account_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, now(), now())
                ON CONFLICT (provider, provider_account_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    updated_at = now()
                """,
                (f"{provider}:{provider_account_id}", stored_user_id, provider, provider_account_id),
            )
            cur.execute(
                """
                INSERT INTO login_events (user_id, provider, email, occurred_at)
                VALUES (%s, %s, %s, now())
                """,
                (stored_user_id, provider, email),
            )
        conn.commit()
    return UserRecord.model_validate(row)