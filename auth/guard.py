import streamlit as st
from auth.users import get_user_by_email
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status

def get_current_email() -> str | None:
    """
    Recupera el email del usuario desde Google Auth o la sesión de Streamlit.
    """
    # 1. Prioridad: Usuario validado por Google Auth
    if "user" in st.session_state:
        user_session = st.session_state["user"]
        # Buscamos el email usando la clave que definimos en google_auth.py
        # mapeada a la columna de Supabase "correo electrónico"
        return user_session.get("correo electrónico", "").lower().strip()

    # 2. Fallback: Otros estados de sesión (opcional)
    email_legacy = st.session_state.get("user_email")
    if email_legacy:
        return str(email_legacy).lower().strip()

    return None

def require_login() -> dict:
    """
    Portero de la aplicación: valida identidad, existencia y estado en Supabase.
    """
    email = get_current_email()
    if not email:
        st.error("Necesitás iniciar sesión con Google para continuar.")
        st.stop()

    # Consultamos la tabla 'usuarios' en Supabase
    user = get_user_by_email(email)
    if not user:
        st.error("Usuario no registrado en Nea Data. Contactanos para darte de alta.")
        st.stop()

    # Validamos el estado según las columnas reales de tu DB
    if user.get("estado") == "suspended":
        st.error("Tu cuenta está suspendida. Contactanos para regularizar tu situación.")
        st.stop()

    if user.get("estado") == "pending":
        st.info("Tu cuenta está pendiente de alta. En breve habilitaremos tu acceso.")
        st.stop()

    # Alerta de expiración de suscripción (Lógica contable)
    if is_subscription_active(user["id"]) and should_show_expiration_alert(user["id"]):
        status = get_usage_status(user["id"])
        dl = status.get("days_left")
        if dl in (7, 5, 3, 1):
            st.info(f"⏳ Tu suscripción vence en **{dl} días**. Evitá interrupciones en tus servicios fiscales.")

    return user

def require_admin() -> dict:
    """
    Restringe el acceso a funciones administrativas (David Solis).
    Sincronizado con el rol 'administración' de Supabase.
    """
    user = require_login()
    # En tu DB el rol es 'administración', no 'admin'
    if user.get("role") not in ["admin", "administración"]:
        st.error("No tenés permisos para acceder a la configuración administrativa.")
        st.stop()
    return user
