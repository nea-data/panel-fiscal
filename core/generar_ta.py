import os
import time
import base64
import datetime
import subprocess
import pickle
import tempfile
import xml.etree.ElementTree as ET

import pytz
import streamlit as st
import zeep

# ======================================================
# CONFIG
# ======================================================
SERVICE = "ws_sr_constancia_inscripcion"
WSDL_AUTH = st.secrets.get(
    "AFIP_WSAA_URL",
    "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL"
)

TZ = pytz.timezone("America/Argentina/Buenos_Aires")

TA_DIR = os.path.join(tempfile.gettempdir(), "afip_ta")
os.makedirs(TA_DIR, exist_ok=True)

TRA_XML = os.path.join(TA_DIR, "TRA.xml")
TRA_SIGNED = os.path.join(TA_DIR, "TRA.cms")
TA_FILE = os.path.join(TA_DIR, f"{SERVICE}.pkl")

# ======================================================
# HELPERS
# ======================================================
def _write_secret_file(secret_key: str, filename: str) -> str:
    content = st.secrets.get(secret_key)
    if not content:
        raise RuntimeError(f"Falta secret {secret_key}")
    path = os.path.join(TA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def _openssl_ok():
    subprocess.run(
        ["openssl", "version"],
        check=True,
        capture_output=True
    )


# ======================================================
# GENERAR TRA
# ======================================================
def _generar_tra():
    now = datetime.datetime.now(TZ)

    root = ET.Element("loginTicketRequest", version="1.0")
    header = ET.SubElement(root, "header")
    ET.SubElement(header, "uniqueId").text = str(int(time.time()))
    ET.SubElement(header, "generationTime").text = (
        now - datetime.timedelta(minutes=5)
    ).isoformat()
    ET.SubElement(header, "expirationTime").text = (
        now + datetime.timedelta(hours=12)
    ).isoformat()

    ET.SubElement(root, "service").text = SERVICE

    with open(TRA_XML, "wb") as f:
        f.write(ET.tostring(root, encoding="utf-8"))


def _firmar_tra(cert_path: str, key_path: str):
    _openssl_ok()
    subprocess.run(
        [
            "openssl", "smime", "-sign",
            "-signer", cert_path,
            "-inkey", key_path,
            "-in", TRA_XML,
            "-out", TRA_SIGNED,
            "-outform", "DER",
            "-nodetach",
        ],
        check=True
    )


# ======================================================
# OBTENER TA
# ======================================================
def _obtener_ta():
    with open(TRA_SIGNED, "rb") as f:
        cms = base64.b64encode(f.read()).decode()

    client = zeep.Client(WSDL_AUTH)
    response = client.service.loginCms(cms)

    root = ET.fromstring(response)
    token = root.findtext(".//token")
    sign = root.findtext(".//sign")
    exp  = root.findtext(".//expirationTime")

    if not token or not sign:
        raise RuntimeError("WSAA no devolvió token/sign")

    expiration = datetime.datetime.fromisoformat(exp)
    if expiration.tzinfo is None:
        expiration = pytz.UTC.localize(expiration)

    expiration = expiration.astimezone(TZ)

    with open(TA_FILE, "wb") as f:
        pickle.dump(
            {"token": token, "sign": sign, "expiration": expiration},
            f
        )

    return token, sign


def _ta_valido():
    if not os.path.exists(TA_FILE):
        return False
    try:
        with open(TA_FILE, "rb") as f:
            ta = pickle.load(f)
        return ta["expiration"] > datetime.datetime.now(TZ)
    except Exception:
        return False


# ======================================================
# API PÚBLICA
# ======================================================
def obtener_o_generar_ta():
    cert_path = _write_secret_file("AFIP_CERT_PEM", "cert.pem")
    key_path  = _write_secret_file("AFIP_KEY_PEM", "key.pem")

    try:
        if not _ta_valido():
            _generar_tra()
            _firmar_tra(cert_path, key_path)
            return _obtener_ta()

        with open(TA_FILE, "rb") as f:
            ta = pickle.load(f)
        return ta["token"], ta["sign"]

    finally:
        for p in (cert_path, key_path):
            try:
                os.remove(p)
            except:
                pass


