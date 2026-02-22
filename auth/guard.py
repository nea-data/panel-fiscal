import streamlit as st
from auth.users import get_user_by_email
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status


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

    # Validamos status correcto
    if user.get("status") == "suspended":
        st.error("Tu cuenta está suspendida.")
        st.stop()

    if user.get("status") == "pending":
        st.info("Tu cuenta está pendiente de activación.")
        st.stop()

    # Alerta vencimiento
    if is_subscription_active(user["id"]) and should_show_expiration_alert(user["id"]):
        status = get_usage_status(user["id"])
        dl = status.get("days_left")
        if dl in (7, 5, 3, 1):
            st.info(f"⏳ Tu suscripción vence en {dl} días.")

    return user


def require_admin() -> dict:
    """
    Restringe acceso a panel administrativo.
    """

    user = require_login()

    if user.get("role") != "admin":
        st.error("No tenés permisos administrativos.")
        st.stop()

    return user
