from typing import Optional, List, Dict
from psycopg2.extras import RealDictCursor
from auth.db import get_connection

# ======================================================
# HELPERS
# ======================================================

def get_user_by_email(email: str) -> Optional[dict]:
    """Busca un usuario por email devolviendo un diccionario."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s LIMIT 1",
            (email.lower().strip(),)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Busca un usuario por ID."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT * FROM users WHERE id = %s LIMIT 1",
            (user_id,)
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


# ======================================================
# LOGIN SIMPLE (SIN PASSWORD)
# ======================================================

def authenticate_user(email: str):
    """
    Autenticación por whitelist.
    Si el email existe y está activo → entra.
    """

    email_clean = email.lower().strip()
    user = get_user_by_email(email_clean)

    if not user:
        return None, "Email no autorizado."

    if user["status"] != "active":
        return None, f"Tu usuario está {user['status']}."

    # Seguridad: nunca devolvemos password_hash
    user.pop("password_hash", None)

    return user, None


# ======================================================
# ADMIN ACTIONS
# ======================================================

def list_users() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, email, name, role, status, created_at, last_login_at
            FROM users
            ORDER BY created_at DESC
        """)
        return cur.fetchall()
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
