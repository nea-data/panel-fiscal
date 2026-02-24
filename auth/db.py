# auth/db.py
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st


def get_connection():
    """
    Conecta a Supabase y configura el cursor para devolver diccionarios.
    """
    try:
        conn = psycopg2.connect(
            st.secrets["postgres"]["url"],
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        # Mantengo tu comportamiento (UI-friendly)
        st.error(f"❌ Error de conexión a NEA DATA DB: {e}")
        st.stop()


def get_conn():
    return get_connection()
