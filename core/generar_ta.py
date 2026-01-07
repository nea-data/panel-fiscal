import base64
import tempfile
from datetime import datetime, timedelta

import streamlit as st
from OpenSSL import crypto
from zeep import Client

# ======================================================
# CONFIG AFIP (SECRETS)
# ======================================================
AFIP_CUIT = st.secrets["AFIP_CUIT"]
WSAA_WSDL = st.secrets["AFIP_WSAA_URL"]
SERVICE = "ws_sr_constancia_inscripcion"

CERT_PEM = st.secrets["AFIP_CERT"]
KEY_PEM  = st.secrets["AFIP_KEY"]

# ======================================================
# UTILIDAD: escribir cert/key temporales
# ======================================================
def _write_tmp_file(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(content.encode("utf-8"))
    f.close()
    return f.name

# ======================================================
# OBTENER / GENERAR TA (CACHEADO)
# ======================================================
@st.cache_data(ttl=60 * 60 * 11)  # 11 horas
def obtener_o_generar_ta():
    cert_path = _write_tmp_file(CERT_PEM, ".crt")
    key_path  = _write_tmp_file(KEY_PEM, ".key")

    login_ticket = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{int(datetime.now().timestamp())}</uniqueId>
        <generationTime>{(datetime.now() - timedelta(minutes=10)).isoformat()}</generationTime>
        <expirationTime>{(datetime.now() + timedelta(hours=12)).isoformat()}</expirationTime>
    </header>
    <service>{SERVICE}</service>
</loginTicketRequest>
"""

    cert = crypto.load_certificate(
        crypto.FILETYPE_PEM,
        open(cert_path, "rb").read()
    )
    key = crypto.load_privatekey(
        crypto.FILETYPE_PEM,
        open(key_path, "rb").read()
    )

    # 🔐 FIRMA PKCS7 (CMS)
    pkcs7 = crypto.sign(
        cert,
        key,
        login_ticket.encode(),
        "sha256",
        crypto.PKCS7_BINARY | crypto.PKCS7_DETACHED
    )

    cms = base64.b64encode(pkcs7).decode()

    client = Client(WSAA_WSDL)
    response = client.service.loginCms(cms)

    if not response or not response.credentials:
        raise RuntimeError("AFIP WSAA no devolvió credenciales")

    return {
        "token": response.credentials.token,
        "sign": response.credentials.sign,
        "expirationTime": response.credentials.expirationTime,
    }


