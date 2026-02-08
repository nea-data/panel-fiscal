import streamlit as st

from auth.users import get_user_by_email
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status


def get_current_email() -> str | None:
    if hasattr(st, "user") and st.user:
        email = getattr(st.user, "email", None)
        if email:
            return str(email).lower()

    email = st.session_state.get("user_email")
    if email:
        return str(email).lower()

    return None


def require_login() -> dict:
    email = get_current_email()
    if not email:
        st.error("Necesitás iniciar sesión para continuar.")
        st.stop()

    user = get_user_by_email(email)
    if not user:
        st.error("Usuario no registrado. Volvé a iniciar sesión.")
        st.stop()

    if user["status"] == "suspended":
        st.error("Tu cuenta está suspendida. Contactanos para regularizar.")
        st.stop()

    if user["status"] == "pending":
        st.info("Tu cuenta está pendiente de alta. En breve vamos a habilitar el acceso.")
        st.stop()

    if is_subscription_active(user["id"]) and should_show_expiration_alert(user["id"]):
        status = get_usage_status(user["id"])
        dl = status.get("days_left")
        if dl in (7, 5):
            st.info(
                f"⏳ Tu suscripción vence en **{dl} días**. "
                "Para evitar interrupciones, contactanos para renovar."
            )

    return user


def require_active_subscription(user: dict) -> None:
    if not is_subscription_active(user["id"]):
        st.warning(
            "No tenés una suscripción activa (o está vencida). "
            "Contactanos para habilitar el acceso."
        )
        st.stop()


def require_admin() -> dict:
    user = require_login()
    if user.get("role") != "admin":
        st.error("No tenés permisos para acceder a esta sección.")
        st.stop()
    return user
