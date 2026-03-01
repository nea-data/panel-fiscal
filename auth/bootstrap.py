from __future__ import annotations

import streamlit as st
from auth.db import get_connection
from auth.passwords import hash_password


def ensure_bootstrap_admin() -> None:
    """
    Crea el usuario admin inicial si no existe.
    Usa st.secrets[bootstrap] y deja must_change_password=true.
    Seguro para Streamlit Cloud (idempotente).
    """
    cfg = st.secrets.get("bootstrap", {})
    admin_email = (cfg.get("admin_email") or "").strip().lower()
    admin_name = (cfg.get("admin_name") or "Admin").strip()
    admin_password = cfg.get("admin_password")

    # Si no está configurado, no hacemos nada.
    if not admin_email or not admin_password:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # ¿Existe?
                cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (admin_email,))
                row = cur.fetchone()
                if row:
                    # Asegurar rol/status admin (opcional pero útil)
                    cur.execute(
                        """
                        UPDATE users
                        SET role='admin', status='active'
                        WHERE email=%s
                        """,
                        (admin_email,),
                    )
                    return

                pw_hash = hash_password(admin_password)

                # Crear admin
                cur.execute(
                    """
                    INSERT INTO users (
                        email, name, role, status,
                        password_hash, must_change_password,
                        created_at, last_login_at
                    )
                    VALUES (
                        %s, %s, 'admin', 'active',
                        %s, true,
                        CURRENT_TIMESTAMP, NULL
                    )
                    """,
                    (admin_email, admin_name, pw_hash),
                )
    finally:
        conn.close()
