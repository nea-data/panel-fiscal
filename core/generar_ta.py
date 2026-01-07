import base64
from datetime import datetime, timedelta
import tempfile

import streamlit as st
from lxml import etree
from zeep import Client

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate


# ======================================================
# CONFIG AFIP
# ======================================================
AFIP_CUIT = st.secrets["AFIP_CUIT"]
WSAA_WSDL = st.secrets["AFIP_WSAA_URL"]
SERVICE = "ws_sr_constancia_inscripcion"


# ======================================================
# FIRMAR LOGIN TICKET (cryptography)
# ======================================================
def _firmar_login_ticket(xml: bytes) -> str:
    cert_pem = st.secrets["AFIP_CERT_PEM"].encode()
    key_pem = st.secrets["AFIP_KEY_PEM"].encode()

    cert = load_pem_x509_certificate(cert_pem)
    private_key = serialization.load_pem_private_key(
        key_pem,
        password=None
    )

    signature = private_key.sign(
        xml,
        padding.PKCS1v15(),
        hashes.SHA256()
    )

    return base64.b64encode(signature).decode()


# ======================================================
# GENERAR CMS
# ======================================================
def _generar_cms() -> str:
    now = datetime.utcnow()

    login_ticket = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{int(now.timestamp())}</uniqueId>
        <generationTime>{(now - timedelta(minutes=5)).isoformat()}</generationTime>
        <expirationTime>{(now + timedelta(minutes=5)).isoformat()}</expirationTime>
    </header>
    <service>{SERVICE}</service>
</loginTicketRequest>
""".encode("utf-8")

    return _firmar_login_ticket(login_ticket)


# ======================================================
# OBTENER TOKEN + SIGN (CACHEADO)
# ======================================================
@st.cache_data(ttl=60 * 60 * 11)  # 11 horas
def obtener_o_generar_ta():
    cms = _generar_cms()

    client = Client(WSAA_WSDL)
    response = client.service.loginCms(cms)

    tree = etree.fromstring(response.encode())
    token = tree.findtext(".//token")
    sign = tree.findtext(".//sign")

    if not token or not sign:
        raise RuntimeError("AFIP WSAA no devolvió token/sign")

    return token, sign

