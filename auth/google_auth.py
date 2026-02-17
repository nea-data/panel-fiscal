import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests
from auth.users import upsert_user_google

def get_google_auth_flow():
    # Construye el flujo usando los secrets
    return Flow.from_client_config(
        {"web": {
            "client_id": st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
            "auth_uri": st.secrets["google"]["auth_uri"],
            "token_uri": st.secrets["google"]["token_uri"],
        }},
        scopes=[
            "openid", 
            "https://www.googleapis.com/auth/userinfo.email", 
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_uri=st.secrets["google"]["redirect_uri"]
    )

def login_google():
    flow = get_google_auth_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    st.markdown(f"""
        <div style="text-align: center;">
            <a href="{auth_url}" target="_self">
                <button style="background-color: #4285F4; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                    🔐 Ingresar con Google
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

def check_google_callback():
    # Si detectamos el código de Google en la URL
    if "code" in st.query_params and "user" not in st.session_state:
        try:
            flow = get_google_auth_flow()
            flow.fetch_token(code=st.query_params["code"])
            
            # Verificamos el token
            id_info = id_token.verify_oauth2_token(
                flow.credentials.id_token, 
                requests.Request(), 
                st.secrets["google"]["client_id"]
            )
            
            # Sincronizamos con Supabase (Tu tabla 'usuarios')
            user_data = upsert_user_google(id_info["email"], id_info.get("name", "Usuario NEA"))
            
            # Guardamos en sesión
            st.session_state["user"] = user_data
            st.session_state["authentication_status"] = True
            
            # Limpiamos URL y recargamos
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error en login: {e}")

