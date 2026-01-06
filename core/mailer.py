import smtplib
from email.message import EmailMessage
from pathlib import Path
import streamlit as st

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


def _get_mail_cfg():
    user = st.secrets.get("SMTP_USER")
    pwd  = st.secrets.get("SMTP_APP_PASSWORD")
    notify_to = st.secrets.get("NOTIFY_TO", user)

    if not user or not pwd:
        raise RuntimeError("Faltan secrets SMTP_USER / SMTP_APP_PASSWORD")

    return user, pwd, notify_to


def enviar_pedido(archivo, email_usuario: str):
    """
    Envía a NEA DATA el pedido recibido desde la app.
    """
    user, pwd, notify_to = _get_mail_cfg()

    bytes_excel = archivo.read()
    nombre_archivo = archivo.name

    msg = EmailMessage()
    msg["Subject"] = "📥 [NEA DATA] Nuevo pedido Emitidos / Recibidos"
    msg["From"] = user
    msg["To"] = notify_to

    msg.set_content(
        f"Se recibió un nuevo pedido desde la app.\n\n"
        f"Email para enviar resultados: {email_usuario}\n"
        f"Archivo adjunto: {nombre_archivo}\n"
    )

    msg.add_attachment(
        bytes_excel,
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nombre_archivo
    )

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.login(user, pwd)
        smtp.send_message(msg)
