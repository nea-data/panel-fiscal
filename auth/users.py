from typing import Optional, List, Dict
from auth.db import get_connection

ADMIN_EMAIL = "neadata.contacto@gmail.com"


def log_admin_action(admin_email: str, action: str, target_user_id: int, details: str = "") -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO admin_actions (admin_email, action, target_user_id, details)
        VALUES (?, ?, ?, ?)
    """, (admin_email, action, target_user_id, details))
    conn.commit()


def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,))
    row = cur.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def upsert_user_on_login(email: str, name: str = "") -> dict:
    """
    Se llama post-login.
    - Si no existe: crea usuario con status=pending (salvo admin) para que el alta sea desde panel admin.
    - Actualiza last_login_at siempre.
    """
    conn = get_connection()
    cur = conn.cursor()

    existing = get_user_by_email(email)

    if not existing:
        role = "admin" if email.lower() == ADMIN_EMAIL.lower() else "user"
        status = "active" if role == "admin" else "pending"

        cur.execute("""
            INSERT INTO users (email, name, role, status, created_at, last_login_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (email, name or "", role, status))
        conn.commit()
        return get_user_by_email(email)

    # Update login + nombre si vino vacío antes
    cur.execute("""
        UPDATE users
        SET last_login_at = CURRENT_TIMESTAMP,
            name = CASE WHEN (name IS NULL OR name = '') THEN ? ELSE name END
        WHERE email = ?
    """, (name or "", email))
    conn.commit()

    return get_user_by_email(email)


def list_users() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, email, name, role, status, created_at, last_login_at
        FROM users
        ORDER BY created_at DESC
    """)
    return [dict(r) for r in cur.fetchall()]


def set_user_status(user_id: int, status: str, admin_email: str) -> None:
    if status not in ("pending", "active", "suspended"):
        raise ValueError("status inválido")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    log_admin_action(admin_email, f"set_status:{status}", user_id)


def set_user_role(user_id: int, role: str, admin_email: str) -> None:
    if role not in ("user", "admin"):
        raise ValueError("role inválido")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    log_admin_action(admin_email, f"set_role:{role}", user_id)
