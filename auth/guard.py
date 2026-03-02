import streamlit as st
from psycopg2.extras import RealDictCursor

from auth.users import get_user_by_email
from auth.subscriptions import is_subscription_active
from auth.service import should_show_expiration_alert, get_usage_status
from auth.db import get_connection


def get_current_email() -> str | None:
    """
    Extrae el email del estado de sesión de Streamlit.
    ✅ Compatible con tu login actual: st.session_state["db_user"]
    (y tolera legacy: st.session_state["user"])
    """
    # Nuevo estándar
    if "db_user" in st.session_state and st.session_state["db_user"]:
        u = st.session_state["db_user"]
        email = u.get("email", "") if isinstance(u, dict) else getattr(u, "email", "")
        return email.lower().strip() if email else None

    # Legacy (por compatibilidad)
    if "user" in st.session_state and st.session_state["user"]:
        u = st.session_state["user"]
        email = u.get("email", "") if isinstance(u, dict) else getattr(u, "email", "")
        return email.lower().strip() if email else None

    return None


def _touch_last_login(user_id: int) -> None:
    """Actualiza last_login_at (audit trail)."""
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (user_id,),
                )
        conn.close()
    except Exception:
        # No frenamos el flujo por un log de auditoría
        pass


def require_login() -> dict:
    """
    Valida que el usuario esté logueado y activo.
    Control interno de acceso.
    """
    email = get_current_email()

    if not email:
        st.error("🔒 Sesión no detectada. Por favor, iniciá sesión para continuar.")
        st.stop()

    # Buscamos al usuario actualizado en DB
    user = get_user_by_email(email)

    if not user:
        st.error("⚠️ Usuario no encontrado. Por favor, contactá al soporte de NEA DATA.")
        st.session_state.clear()
        st.stop()

    user_dict = dict(user)

    # --- Auditoría ---
    if user_dict.get("id"):
        _touch_last_login(int(user_dict["id"]))

    # --- Validación de estado ---
    status = user_dict.get("status")
    if status == "suspended":
        st.error("🚫 Tu cuenta está suspendida por falta de pago o infracción de términos.")
        st.stop()

    if status == "pending":
        st.info("🕒 Tu cuenta está en proceso de revisión por NEA DATA.")
        st.stop()

    # --- Admin bypass total ---
    if user_dict.get("role") == "admin":
        return user_dict

    # --- Validación de suscripción ---
    try:
        if not is_subscription_active(int(user_dict["id"])):
            st.error("💳 Tu suscripción ha vencido. Contactanos para renovarla y seguir operando.")
            st.stop()
    except Exception as e:
        st.error(f"Error al validar suscripción: {e}")
        st.stop()

    # --- Alertas de vencimiento (no bloqueantes) ---
    try:
        if should_show_expiration_alert(int(user_dict["id"])):
            status_info = get_usage_status(int(user_dict["id"]))
            dl = status_info.get("days_left")
            if dl is not None and dl <= 7:
                st.warning(f"⏳ Aviso: Tu suscripción de NEA DATA vence en {dl} días.")
    except Exception:
        pass

    return user_dict


def require_admin() -> dict:
    """
    Protege rutas administrativas y de configuración global.
    """
    user = require_login()

    if user.get("role") != "admin":
        st.error("🛑 Acceso denegado: Se requieren permisos de administrador de NEA DATA.")
        st.stop()

    return user
