import streamlit as st
from auth.users import get_user_by_email # Cambiado: antes buscaba upsert_user_google
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status

def get_current_email() -> str | None:
    """Extrae el email del estado de sesión de Streamlit."""
    if "user" in st.session_state and st.session_state["user"]:
        return (
            st.session_state["user"]
            .get("email", "")
            .lower()
            .strip()
        )
    return None

def require_login() -> dict:
    """Valida que el usuario esté logueado y activo."""
    email = get_current_email()

    if not email:
        st.error("Necesitás iniciar sesión para continuar.")
        st.stop()

    # Buscamos al usuario en la base de datos SQL
    user = get_user_by_email(email)

    if not user:
        st.error("Usuario no encontrado en la base de datos.")
        st.stop()

    # =============================
    # VALIDACIÓN DE ESTADO
    # =============================
    if user.get("status") == "suspended":
        st.error("Tu cuenta está suspendida. Contactá al soporte de Nea Data.")
        st.stop()

    if user.get("status") == "pending":
        st.info("Tu cuenta está pendiente de activación.")
        st.stop()

    # =============================
    # ADMIN BYPASS TOTAL
    # =============================
    if user.get("role") == "admin":
        return dict(user)

    # =============================
    # VALIDACIÓN DE SUSCRIPCIÓN
    # =============================
    if not is_subscription_active(user["id"]):
        st.error("Tu suscripción ha vencido. Contactanos para renovarla.")
        st.stop()

    # =============================
    # ALERTA DE VENCIMIENTO
    # =============================
    try:
        if should_show_expiration_alert(user["id"]):
            status = get_usage_status(user["id"])
            dl = status.get("days_left")
            if dl in (7, 5, 3, 1):
                st.warning(f"⏳ Tu suscripción de Nea Data vence en {dl} días.")
    except Exception:
        pass

    return dict(user)

def require_admin() -> dict:
    """Protege rutas administrativas."""
    user = require_login()
    if user.get("role") != "admin":
        st.error("No tenés permisos administrativos.")
        st.stop()
    return user
