import streamlit as st
from auth.users import get_user_by_email
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status
from auth.db import get_connection


# =====================================================
# 1️⃣ Obtener email desde Google Auth
# =====================================================
def get_current_email() -> str | None:
    """
    Recupera el email del usuario desde Google Auth.
    """

    if "user" in st.session_state:
        return (
            st.session_state["user"]
            .get("email", "")
            .lower()
            .strip()
        )

    return None


# =====================================================
# 2️⃣ Registrar último inicio de sesión
# =====================================================
def update_last_login(user_id: int):
    """
    Actualiza el último inicio de sesión en la tabla usuarios.
    Se ejecuta solo una vez por sesión.
    """

    try:
        conn = get_connection()

        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE usuarios
                    SET ultimo_inicio_de_sesion_en = NOW()
                    WHERE id = %s
                """, (user_id,))

        conn.close()

    except Exception as e:
        # No detenemos la app si falla este update
        print("⚠️ Error actualizando último login:", e)


# =====================================================
# 3️⃣ Requiere login válido
# =====================================================
def require_login() -> dict:
    """
    Valida identidad, existencia y estado en Supabase.
    """

    email = get_current_email()

    if not email:
        st.error("Necesitás iniciar sesión con Google para continuar.")
        st.stop()

    user = get_user_by_email(email)

    if not user:
        st.error("Usuario no registrado en Nea Data.")
        st.stop()

    # -------------------------------------------------
    # Registrar login SOLO una vez por sesión
    # -------------------------------------------------
    if "login_recorded" not in st.session_state:
        update_last_login(user["id"])
        st.session_state["login_recorded"] = True

    # -------------------------------------------------
    # Validar estado
    # -------------------------------------------------
    if user.get("status") == "suspended":
        st.error("Tu cuenta está suspendida.")
        st.stop()

    if user.get("status") == "pending":
        st.info("Tu cuenta está pendiente de activación.")
        st.stop()

    # -------------------------------------------------
    # Alerta vencimiento de suscripción
    # -------------------------------------------------
    try:
        if is_subscription_active(user["id"]) and should_show_expiration_alert(user["id"]):
            status = get_usage_status(user["id"])
            dl = status.get("days_left")

            if dl in (7, 5, 3, 1):
                st.info(f"⏳ Tu suscripción vence en {dl} días.")

    except Exception as e:
        # No rompemos login si falla módulo de suscripciones
        print("⚠️ Error verificando suscripción:", e)

    return user


# =====================================================
# 4️⃣ Requiere rol administrador
# =====================================================
def require_admin() -> dict:
    """
    Restringe acceso a panel administrativo.
    """

    user = require_login()

    if user.get("role") not in ["admin", "administración"]:
        st.error("No tenés permisos administrativos.")
        st.stop()

    return user
