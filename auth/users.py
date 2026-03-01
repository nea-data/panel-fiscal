from typing import Optional, List, Dict
from psycopg2.extras import RealDictCursor
from auth.db import get_connection
from auth.subscriptions import create_subscription, get_active_subscription
from auth.passwords import hash_password, verify_password

# ======================================================
# CONFIG
# ======================================================

ADMIN_EMAIL = "neadata.contacto@gmail.com"


# ======================================================
# HELPERS
# ======================================================

def get_user_by_email(email: str) -> Optional[dict]:
    """Busca un usuario por email devolviendo un diccionario."""
    conn = get_connection()
    # Usamos RealDictCursor para evitar el casteo manual dict(row)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s LIMIT 1",
            (email.lower().strip(),)
        )
        row = cur.fetchone()
        return row # Ya es un dict o None
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
# LOGIN / AUTHENTICATION
# ======================================================

def authenticate_user(email: str, password: str):
    """
    Lógica de autenticación principal.
    Resuelve el error de passlib usando la verificación nativa de bcrypt.
    """
    email_clean = email.lower().strip()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            "SELECT * FROM users WHERE email = %s LIMIT 1",
            (email_clean,)
        )
        user = cur.fetchone()

        if not user:
            return None, "Usuario no encontrado."

        if user["status"] in ("pending", "suspended"):
            return None, f"Tu usuario está {user['status']}. Contactá al soporte."

        if not user.get("password_hash"):
            return None, "Usuario sin contraseña asignada (registrado vía Google u otro)."

        # Verificación de password (ahora usa bcrypt directo)
        # Manejamos el caso de que la DB devuelva el hash como bytes o memoryview
        stored_hash = user["password_hash"]
        if hasattr(stored_hash, 'tobytes'): # Para memoryview de PostgreSQL
            stored_hash = stored_hash.tobytes().decode('utf-8')
        elif isinstance(stored_hash, bytes):
            stored_hash = stored_hash.decode('utf-8')

        if not verify_password(password, stored_hash):
            return None, "Email o contraseña incorrectos."

        # Actualizar rastro de auditoría (importante para contabilidad/seguridad)
        cur.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user["id"],)
        )
        conn.commit()

        # Limpiamos el hash del diccionario por seguridad antes de devolverlo a Streamlit
        user.pop("password_hash", None)
        return dict(user), None

    except Exception as e:
        return None, f"Error en el servidor: {str(e)}"
    finally:
        cur.close()
        conn.close()

# ======================================================
# ADMIN ACTIONS
# ======================================================

def list_users() -> List[Dict]:
    """Lista todos los usuarios omitiendo datos sensibles."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT id, email, full_name, role, status, created_at, last_login_at 
            FROM users 
            ORDER BY created_at DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def set_user_status(user_id: int, status: str, admin_email: str) -> None:
    """Cambia el estado del usuario (Control de acceso)."""
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
    """Cambia el rol (user/admin)."""
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
