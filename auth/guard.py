import streamlit as st
from auth.users import upsert_user_google
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status


def get_current_email() -> str | None:
    if "user" in st.session_state:
        return (
            st.session_state["user"]
            .get("email", "")
            .lower()
            .strip()
        )
    return None


def require_login() -> dict:

    email = get_current_email()

    if not email:
        st.error("Necesitás iniciar sesión con Google para continuar.")
        st.stop()

    # 🔥 Importante: esto crea/actualiza usuario pero NO crea suscripción
    user = upsert_user_google(email)

    # =============================
    # VALIDACIÓN DE ESTADO
    # =============================
    if user.get("status") == "suspended":
        st.error("Tu cuenta está suspendida.")
        st.stop()

    if user.get("status") == "pending":
        st.info("Tu cuenta está pendiente de activación.")
        st.stop()

    # =============================
    # ADMIN BYPASS TOTAL
    # =============================
    if user.get("role") == "admin":
        return user

    # =============================
    # VALIDACIÓN REAL DE SUSCRIPCIÓN
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
                st.warning(f"⏳ Tu suscripción vence en {dl} días.")
    except Exception:
        pass

    return user


def require_admin() -> dict:
    user = require_login()

    if user.get("role") != "admin":
        st.error("No tenés permisos administrativos.")
        st.stop()

    return user
