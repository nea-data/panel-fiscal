# core/emitidos_recibidos.py

from typing import Dict, List
import pandas as pd


REQUIRED_COLUMNS = {
    "CUIT",
    "EMITIDOS",
    "RECIBIDOS"
}


def validar_excel_pedido(df: pd.DataFrame) -> Dict:
    """
    Valida la estructura del Excel subido por el cliente.

    Reglas:
    - Debe existir CUIT
    - Debe existir EMITIDOS y/o RECIBIDOS
    - No ejecuta ninguna automatización
    """

    columnas = set(df.columns.str.upper())

    faltantes = REQUIRED_COLUMNS - columnas
    if faltantes:
        return {
            "ok": False,
            "error": f"Faltan columnas obligatorias: {', '.join(faltantes)}"
        }

    # Normalizar nombres
    df.columns = df.columns.str.upper()

    total = len(df)

    emitidos = df["EMITIDOS"].astype(str).str.lower().isin(["1", "si", "sí", "true"]).sum()
    recibidos = df["RECIBIDOS"].astype(str).str.lower().isin(["1", "si", "sí", "true"]).sum()

    return {
        "ok": True,
        "total_clientes": total,
        "con_emitidos": int(emitidos),
        "con_recibidos": int(recibidos)
    }


def resumen_pedido(df: pd.DataFrame, email_destino: str) -> Dict:
    """
    Devuelve un resumen estructurado del pedido.
    Se usa SOLO para mostrar o enviar por mail.
    """

    validacion = validar_excel_pedido(df)
    if not validacion["ok"]:
        return validacion

    return {
        "ok": True,
        "email_destino": email_destino,
        "total_clientes": validacion["total_clientes"],
        "emitidos": validacion["con_emitidos"],
        "recibidos": validacion["con_recibidos"],
        "mensaje": (
            f"Pedido recibido correctamente.\n"
            f"Clientes: {validacion['total_clientes']}\n"
            f"Emitidos: {validacion['con_emitidos']}\n"
            f"Recibidos: {validacion['con_recibidos']}"
        )
    }
