from typing import Optional, List, Dict
from auth.db import get_connection
from auth.subscriptions import create_subscription, get_active_subscription

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
    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s LIMIT 1",
            (email.lower().strip(),)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM users WHERE id = %s LIMIT 1",
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


# ======================================================
# LOGIN / UPSERT (Google Auth)
# ======================================================

def upsert_user_google(email: str, name: str = "") -> dict:
    """
    Crea o actualiza usuario al loguearse con Google.
    Si es usuario nuevo → crea plan FREE por 7 días.
    """

    conn = get_connection()
    cur = conn.cursor()

    email_clean = email.lower().strip()
    user = get_user_by_email(email_clean)

    try:
        if not user:

            role = "admin" if email_clean == ADMIN_EMAIL.lower() else "user"
            status = "active"

            cur.execute(
                """
                INSERT INTO users (email, name, role, status, created_at, last_login_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (email_clean, name or "", role, status)
            )

            conn.commit()

            new_user = get_user_by_email(email_clean)

            # 🔥 Si no es admin → crear FREE automáticamente
            if role != "admin":
                create_subscription(
                    user_id=new_user["id"],
                    plan_code="FREE"
                )

            return new_user

        # ==========================
        # Usuario existente
        # ==========================

        cur.execute(
            """
            UPDATE users
            SET last_login_at = CURRENT_TIMESTAMP,
                name = CASE WHEN name IS NULL OR name = '' THEN %s ELSE name END
            WHERE email = %s
            """,
            (name or "", email_clean)
        )

        conn.commit()

        # 🔥 Si no tiene suscripción activa → no crear nada automático
        # El bloqueo lo maneja guard.py

        return get_user_by_email(email_clean)

    finally:
        cur.close()
        conn.close()


# ======================================================
# ADMIN ACTIONS
# ======================================================

def list_users() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def set_user_status(user_id: int, status: str, admin_email: str) -> None:
    if status not in ("pending", "active", "suspended"):
        raise ValueError("Estado inválido")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET status = %s WHERE id = %s",
            (status, user_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def set_user_role(user_id: int, role: str, admin_email: str) -> None:
    if role not in ("user", "admin"):
        raise ValueError("Rol inválido")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET role = %s WHERE id = %s",
            (role, user_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
