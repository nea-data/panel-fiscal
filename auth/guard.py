import streamlit as st
from auth.users import get_user_by_email 
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status

def get_current_email() -> str | None:
    """
    Extrae el email del estado de sesión de Streamlit.
    Compatible con tu sistema de login manual.
    """
    if "user" in st.session_state and st.session_state["user"]:
        # Manejamos si st.session_state["user"] es un objeto o un dict
        user_data = st.session_state["user"]
        email = user_data.get("email", "") if isinstance(user_data, dict) else getattr(user_data, "email", "")
        
        return email.lower().strip() if email else None
    return None

def require_login() -> dict:
    """
    Valida que el usuario esté logueado y activo.
    Actúa como el 'Control Interno' de acceso para los estudios contables.
    """
    email = get_current_email()

    if not email:
        st.error("🔒 Sesión no detectada. Por favor, iniciá sesión para continuar.")
        st.stop()

    # Buscamos al usuario actualizado en la base de datos SQL
    user = get_user_by_email(email)

    if not user:
        st.error("⚠️ Usuario no encontrado. Por favor, contactá al soporte de Nea Data.")
        st.session_state.clear() # Limpiamos sesión corrupta
        st.stop()

    # Convertimos a dict para asegurar consistencia en el manejo de datos
    user_dict = dict(user)

    # ======================================================
    # VALIDACIÓN DE ESTADO (Normativa de seguridad)
    # ======================================================
    if user_dict.get("status") == "suspended":
        st.error("🚫 Tu cuenta está suspendida por falta de pago o infracción de términos.")
        st.stop()

    if user_dict.get("status") == "pending":
        st.info("🕒 Tu cuenta está en proceso de revisión por Nea Data.")
        st.stop()

    # ======================================================
    # ADMIN BYPASS TOTAL
    # ======================================================
    if user_dict.get("role") == "admin":
        return user_dict

    # ======================================================
    # VALIDACIÓN DE SUSCRIPCIÓN (Regla de Negocio)
    # ======================================================
    try:
        if not is_subscription_active(user_dict["id"]):
            st.error("💳 Tu suscripción ha vencido. Contactanos para renovarla y seguir operando.")
            st.stop()
    except Exception as e:
        # Si falla la validación por DB, por seguridad frenamos el acceso
        st.error(f"Error al validar suscripción: {e}")
        st.stop()

    # ======================================================
    # ALERTA DE VENCIMIENTO (UX para el Contador)
    # ======================================================
    try:
        if should_show_expiration_alert(user_dict["id"]):
            status = get_usage_status(user_dict["id"])
            dl = status.get("days_left")
            if dl is not None and dl <= 7:
                st.warning(f"⏳ Aviso: Tu suscripción de Nea Data vence en {dl} días.")
    except Exception:
        # Fallo silencioso en alertas para no interrumpir el flujo principal
        pass

    return user_dict

def require_admin() -> dict:
    """
    Protege rutas administrativas y de configuración global.
    """
    user = require_login()
    
    if user.get("role") != "admin":
        st.error("🛑 Acceso denegado: Se requieren permisos de administrador de Nea Data.")
        st.stop()
        
    return user
