import smtplib
from email.message import EmailMessage


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


def enviar_pedido(
    archivo,
    smtp_user: str,
    smtp_password: str,
    notify_to: str,
):
    """
    Envía a NEA DATA el pedido Emitidos / Recibidos recibido desde la app.
    """

    try:
        bytes_excel = archivo.read()
        nombre_archivo = archivo.name

        msg = EmailMessage()
        msg["Subject"] = "📥 [NEA DATA] Nuevo pedido Emitidos / Recibidos"
        msg["From"] = smtp_user
        msg["To"] = notify_to

        msg.set_content(
            "Se recibió un nuevo pedido desde la app de NEA DATA.\n\n"
            f"Archivo adjunto: {nombre_archivo}\n"
            "Estado: pendiente de procesamiento.\n"
        )

        msg.add_attachment(
            bytes_excel,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=nombre_archivo,
        )

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

    except Exception as e:
        raise RuntimeError("Error enviando el pedido por correo") from e

