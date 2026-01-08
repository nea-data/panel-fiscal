import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465


def enviar_pedido(
    archivo,
    email_resultado: str,
    smtp_user: str,
    smtp_password: str,
    notify_to: str,
):
    """
    Envía a NEA DATA el pedido Emitidos / Recibidos recibido desde la app,
    indicando el correo donde deben enviarse los resultados.
    """

    try:
        # Leer archivo adjunto
        bytes_excel = archivo.read()
        nombre_archivo = archivo.name

        # Construcción del mail
        msg = EmailMessage()
        msg["Subject"] = "📥 [NEA DATA] Pedido Emitidos / Recibidos"
        msg["From"] = smtp_user
        msg["To"] = notify_to

        msg.set_content(
            "Se recibió un nuevo pedido desde la app de NEA DATA.\n\n"
            f"📄 Archivo adjunto: {nombre_archivo}\n"
            f"📧 Enviar resultados a: {email_resultado}\n\n"
            "Estado del pedido: pendiente de procesamiento.\n\n"
            "Nota: la información enviada se utiliza únicamente para el "
            "procesamiento solicitado y no se almacenan credenciales fiscales."
        )

        # Adjuntar Excel
        msg.add_attachment(
            bytes_excel,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=nombre_archivo,
        )

        # Envío
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

    except Exception as e:
        raise RuntimeError(f"Error enviando el pedido por correo: {e}") from e


