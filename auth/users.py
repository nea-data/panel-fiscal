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
from auth.passwords import hash_password, verify_password


def authenticate_user(email: str, password: str):

    email_clean = email.lower().strip()

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s LIMIT 1",
            (email_clean,)
        )
        user = cur.fetchone()

        if not user:
            return None, "Usuario no encontrado."

        user = dict(user)

        if user["status"] in ("pending", "suspended"):
            return None, "Tu usuario no está activo."

        if not user.get("password_hash"):
            return None, "Usuario sin contraseña asignada."

        if not verify_password(password, user["password_hash"]):
            return None, "Email o contraseña incorrectos."

        # Actualizar último login
        cur.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user["id"],)
        )
        conn.commit()

        user.pop("password_hash", None)
        return user, None

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
