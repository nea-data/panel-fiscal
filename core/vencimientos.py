import pandas as pd
from datetime import date

RUTA_EXCEL = "data/vencimientos_anuales.xlsx"


def cargar_vencimientos():
    df = pd.read_excel(RUTA_EXCEL)

    # Normalización defensiva
    df.columns = df.columns.str.lower().str.strip()
    df["organismo"] = df["organismo"].astype(str).str.upper().str.strip()
    df["impuesto"] = df["impuesto"].astype(str).str.upper().str.strip()
    df["terminacion"] = df["terminacion"].astype(str).str.strip()

    return df


def filtrar_vencimientos(
    mostrar_arca=True,
    mostrar_dgr=True,
    mostrar_atp_chaco=False,
    mostrar_tasa_municipal=False,
):
    df = cargar_vencimientos()

    hoy = date.today()
    mes_actual = hoy.month

    filtros = []

    # =========================
    # ORGANISMOS
    # =========================
    if mostrar_arca:
        filtros.append(df["organismo"] == "ARCA")

    if mostrar_dgr:
        filtros.append(df["organismo"] == "DGR")

    if mostrar_atp_chaco:
        filtros.append(df["organismo"] == "ATP(CHACO)")

    # =========================
    # IMPUESTOS
    # =========================
    if mostrar_tasa_municipal:
        filtros.append(df["impuesto"] == "TS")

    if not filtros:
        return pd.DataFrame()

    df = df[pd.concat(filtros, axis=1).any(axis=1)]

    # Solo mes actual
    df = df[df["mes"] == mes_actual]

    # Fecha real
    df["fecha"] = pd.to_datetime(
        dict(year=hoy.year, month=df["mes"], day=df["dia"]),
        errors="coerce",
    )

    df = df.sort_values("fecha")

    return df[
        ["organismo", "impuesto", "terminacion", "fecha"]
    ]
