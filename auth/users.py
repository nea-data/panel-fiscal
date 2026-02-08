from typing import Optional, List, Dict
from auth.db import get_connection

# ======================================================
# CONFIG
# ======================================================

ADMIN_EMAIL = "neadata.contacto@gmail.com"


# ======================================================
# HELPERS
# ======================================================

def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE email = ? LIMIT 1",
        (email,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE id = ? LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


# ======================================================
# LOGIN / UPSERT
# ======================================================

def upsert_user_on_login(email: str, name: str = "") -> dict:
    conn = get_connection()
    cur = conn.cursor()

    user = get_user_by_email(email)

    if not user:
        role = "admin" if email.lower() == ADMIN_EMAIL.lower() else "user"
        status = "active" if role == "admin" else "pending"

        cur.execute(
            """
            INSERT INTO users (email, full_name, role, status, created_at, last_login)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (email, name or "", role, status)
        )
        conn.commit()
        return get_user_by_email(email)

    cur.execute(
        """
        UPDATE users
        SET
            last_login = CURRENT_TIMESTAMP,
            full_name = CASE
                WHEN full_name IS NULL OR full_name = ''
                THEN ?
                ELSE full_name
            END
        WHERE email = ?
        """,
        (name or "", email)
    )
    conn.commit()

    return get_user_by_email(email)


# ======================================================
# ADMIN ACTIONS
# ======================================================

def list_users() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, email, full_name, role, status, created_at, last_login
        FROM users
        ORDER BY created_at DESC
        """
    )
    return [dict(r) for r in cur.fetchall()]


def set_user_status(user_id: int, status: str) -> None:
    if status not in ("pending", "active", "suspended"):
        raise ValueError("Estado inválido")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET status = ? WHERE id = ?",
        (status, user_id)
    )
    conn.commit()


def set_user_role(user_id: int, role: str) -> None:
    if role not in ("user", "admin"):
        raise ValueError("Rol inválido")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET role = ? WHERE id = ?",
        (role, user_id)
    )
    conn.commit()
