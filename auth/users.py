from typing import Optional, List, Dict
import psycopg2.extras
from auth.db import get_connection

# ======================================================
# CONFIG
# ======================================================
# Usamos tu correo como administrador principal
ADMIN_EMAIL = "neadata.contacto@gmail.com"

# ======================================================
# HELPERS (Sincronizados con Supabase)
# ======================================================

def get_user_by_email(email: str) -> Optional[dict]:
    conn = get_connection()
    # Usamos el cursor que ya viene con RealDictCursor desde db.py
    cur = conn.cursor()
    try:
        # ⚠️ IMPORTANTE: Comillas dobles por el espacio en "correo electrónico"
        cur.execute(
            'SELECT * FROM users WHERE email = %s LIMIT 1',
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
        cur.execute('SELECT * FROM usuarios WHERE id = %s LIMIT 1', (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()

# ======================================================
# LOGIN / UPSERT (Para Google Auth)
# ======================================================

def upsert_user_google(email: str, name: str = "") -> dict:
    """
    Registra o actualiza al usuario al ingresar con Google.
    Maneja el rol de administración automáticamente para David.
    """
    conn = get_connection()
    cur = conn.cursor()
    email_clean = email.lower().strip()
    user = get_user_by_email(email_clean)

    try:
        if not user:
            # Lógica de Rol Híbrido: Admin para David, Usuario para clientes
            role = "administración" if email_clean == ADMIN_EMAIL.lower() else "usuario"
            estado = "activo" if role == "administración" else "pending"

            cur.execute(
                """
                INSERT INTO usuarios (email, nombre, role, estado, created_at, last_login_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (email_clean, name or "", role, estado)
            )
            conn.commit()
            return get_user_by_email(email_clean)

        # Actualizamos último acceso
        cur.execute(
            """
            UPDATE usuarios
            SET last_login_at = CURRENT_TIMESTAMP,
                nombre = CASE WHEN nombre IS NULL OR nombre = '' THEN %s ELSE nombre END
            WHERE "correo electrónico" = %s
            """,
            (name or "", email_clean)
        )
        conn.commit()
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
        cur.execute('SELECT * FROM usuarios ORDER BY created_at DESC')
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()

def set_user_status(user_id: int, status: str) -> None:
    # Ajustado a tus estados de Supabase
    if status not in ("pending", "activo", "suspended"):
        raise ValueError("Estado inválido")

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE usuarios SET estado = %s WHERE id = %s", (status, user_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()
