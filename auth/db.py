import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

def get_connection():
    """
    Establece conexión con la base de datos de Supabase (Postgres).
    La URL se toma de st.secrets["postgres"]["url"].
    """
    try:
        # Usamos la URL de conexión de tus secrets
        conn = psycopg2.connect(st.secrets["postgres"]["url"])
        return conn
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        st.stop()

def get_conn():
    return get_connection()
