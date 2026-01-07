import streamlit as st
from zeep import Client, Transport

from core.generar_ta import obtener_o_generar_ta

# ======================================================
# CONFIGURACIÓN AFIP
# ======================================================
WSDL_PADRON = st.secrets.get(
    "AFIP_WSDL_PADRON_A5",
    "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl",
)

CUIT_EMISOR = st.secrets["AFIP_CUIT"]
ZEEP_TRANSPORT = Transport(timeout=20)

# ======================================================
# HELPERS
# ======================================================
def _norm_cuit(x: str) -> str:
    return "".join(ch for ch in str(x) if ch.isdigit())

# ======================================================
# CONSULTA CUIT
# ======================================================
def consultar_cuit(cuit: str) -> dict:
    cuit_norm = _norm_cuit(cuit)

    if not cuit_norm.isdigit() or len(cuit_norm) != 11:
        return {
            "CUIT": cuit_norm,
            "Error": "CUIT inválido (debe tener 11 dígitos)"
        }

    try:
        # Obtener TA válido (cacheado)
        ta = obtener_o_generar_ta()
        token = ta["token"]
        sign = ta["sign"]
    except Exception as e:
        return {
            "CUIT": cuit_norm,
            "Error": f"No se pudo autenticar con AFIP (WSAA): {e}"
        }

    try:
        client = Client(WSDL_PADRON, transport=ZEEP_TRANSPORT)
        respuesta = client.service.getPersonaList_v2(
            token,
            sign,
            CUIT_EMISOR,
            [cuit_norm]
        )
    except Exception as e:
        return {
            "CUIT": cuit_norm,
            "Error": f"Error consultando AFIP: {e}"
        }

    personas = getattr(respuesta, "persona", None)
    if not personas:
        return {
            "CUIT": cuit_norm,
            "Error": "Sin resultados en AFIP"
        }

    persona = personas[0]
    datos = getattr(persona, "datosGenerales", None)

    if not datos:
        return {
            "CUIT": cuit_norm,
            "Error": "AFIP no devolvió datos generales"
        }

    domicilio = getattr(datos, "domicilioFiscal", None)

    razon_social = getattr(datos, "razonSocial", "") or ""
    nombre = getattr(datos, "nombre", "") or ""
    apellido = getattr(datos, "apellido", "") or ""
    nombre_completo = f"{nombre} {apellido}".strip()

    # ======================================================
    # ACTIVIDADES
    # ======================================================
    actividades = []

    if hasattr(persona, "datosRegimenGeneral") and hasattr(
        persona.datosRegimenGeneral, "actividad"
    ):
        actividades = persona.datosRegimenGeneral.actividad

    elif hasattr(persona, "datosMonotributo"):
        mono = persona.datosMonotributo
        if hasattr(mono, "actividad"):
            actividades = mono.actividad
        elif hasattr(mono, "actividadMonotributista"):
            actividades = [mono.actividadMonotributista]

    actividad_principal = ""
    actividades_secundarias = []

    for act in actividades or []:
        desc = getattr(act, "descripcionActividad", "Sin descripción")
        cod = getattr(act, "idActividad", "Sin código")
        orden = getattr(act, "orden", None)

        info = f"{desc} (Código: {cod})"

        if orden == 1 and not actividad_principal:
            actividad_principal = info
        else:
            actividades_secundarias.append(info)

    if not actividad_principal and actividades_secundarias:
        actividad_principal = actividades_secundarias[0]
        actividades_secundarias = actividades_secundarias[1:]

    actividades_secundarias = actividades_secundarias[:4]

    # ======================================================
    # RESPUESTA FINAL
    # ======================================================
    return {
        "CUIT": cuit_norm,
        "Razón Social / Nombre": razon_social or nombre_completo,
        "Domicilio": getattr(domicilio, "direccion", "No disponible") if domicilio else "No disponible",
        "Localidad": getattr(domicilio, "localidad", "No disponible") if domicilio else "No disponible",
        "Provincia": getattr(domicilio, "descripcionProvincia", "No disponible") if domicilio else "No disponible",
        "Actividad Principal": actividad_principal or "No encontrada",
        "Actividad Secundaria 1": actividades_secundarias[0] if len(actividades_secundarias) > 0 else "",
        "Actividad Secundaria 2": actividades_secundarias[1] if len(actividades_secundarias) > 1 else "",
        "Actividad Secundaria 3": actividades_secundarias[2] if len(actividades_secundarias) > 2 else "",
        "Actividad Secundaria 4": actividades_secundarias[3] if len(actividades_secundarias) > 3 else "",
    }


