import os
import pickle
import base64
from datetime import datetime, timedelta
import streamlit as st

from OpenSSL import crypto
from zeep import Client

# ======================================================
# CONFIGURACIÓN AFIP DESDE SECRETS
# ======================================================
CUIT_EMISOR = st.secrets["AFIP_CUIT"]
WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"

TA_DIR = "TA"
TA_PATH = os.path.join(TA_DIR, "ws_sr_constancia_inscripcion.pkl")

CERT_PATH = "afip_cert.crt"
KEY_PATH = "afip_key.key"

# ======================================================
# PREPARAR CERTIFICADO Y KEY (DESDE SECRETS)
# ======================================================
def preparar_certificados():
    if not os.path.exists(CERT_PATH):
        with open(CERT_PATH, "w") as f:
            f.write(st.secrets["AFIP_CERT"])

    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "w") as f:
            f.write(st.secrets["AFIP_KEY"])

# ======================================================
# VERIFICAR TA VIGENTE
# ======================================================
def ta_vigente(ta):
    exp = datetime.fromisoformat(ta["expirationTime"])
    return datetime.now() < exp - timedelta(minutes=5)

# ======================================================
# GENERAR TA NUEVO
# ======================================================
def generar_ta():
    preparar_certificados()
    os.makedirs(TA_DIR, exist_ok=True)

    # Crear Login Ticket Request
    login_ticket = f"""<?xml version="1.0" encoding="UTF-8"?>
    <loginTicketRequest version="1.0">
        <header>
            <uniqueId>{int(datetime.now().timestamp())}</uniqueId>
            <generationTime>{(datetime.now() - timedelta(minutes=10)).isoformat()}</generationTime>
            <expirationTime>{(datetime.now() + timedelta(hours=12)).isoformat()}</expirationTime>
        </header>
        <service>ws_sr_constancia_inscripcion</service>
    </loginTicketRequest>
    """

    # Firmar con OpenSSL
    with open(CERT_PATH, "rb") as f:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

    with open(KEY_PATH, "rb") as f:
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, f.read())

    pkcs7 = crypto.sign(cert, key, login_ticket.encode(), "sha256")
    cms = base64.b64encode(pkcs7).decode()

    # Login CMS
    client = Client("https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl")
    response = client.service.loginCms(cms)

    ta = {
        "token": response.credentials.token,
        "sign": response.credentials.sign,
        "expirationTime": response.credentials.expirationTime
    }

    with open(TA_PATH, "wb") as f:
        pickle.dump(ta, f)

    return ta

# ======================================================
# OBTENER O GENERAR TA
# ======================================================
def obtener_o_generar_ta():
    if os.path.exists(TA_PATH):
        with open(TA_PATH, "rb") as f:
            ta = pickle.load(f)
        if ta_vigente(ta):
            return ta

    return generar_ta()
