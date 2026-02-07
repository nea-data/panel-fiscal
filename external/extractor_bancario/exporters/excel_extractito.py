import os
from datetime import datetime
import pandas as pd

from core.models import ExtractionResult


class ExtractitoExcelExporter:
    """
    Exportador EXTRACTITO BANCARIO
    Output contable estándar (una hoja)
    Compatible multi-banco
    """

    # =====================================================
    # IMPUTACIÓN CONTABLE AUTOMÁTICA
    # =====================================================
    @staticmethod
    def _map_imputacion(description: str) -> str:
        d = (description or "").upper()

        if "LEY 25413" in d:
            return "Impuesto al debito"
        if "SIRCREB" in d:
            return "Sircreb"
        if "IIBB" in d:
            return "IIBB"
        if "CHEQUE" in d:
            return "Valores a depositar"
        if "ACRED" in d:
            return "Valores a depositar"
        if "TRF" in d or "TRANSFER" in d:
            return "Transferencias"
        if "INTERES" in d:
            return "Intereses"
        if "COMISION" in d:
            return "Gastos bancarios"

        return "A clasificar"

    # =====================================================
    # EXPORT PRINCIPAL
    # =====================================================
    @classmethod
    def export(cls, result: ExtractionResult, output_folder: str) -> str:
        rows = []

        fuente = result.profile.file_name

        # =========================
        # SALDO INICIAL (PRIMERA FILA)
        # =========================
        if result.meta and result.meta.opening_balance is not None:
            rows.append({
                "fecha": result.meta.period_start,
                "descripcion": "Saldo Inicial",
                "importe": result.meta.opening_balance,
                "saldo": result.meta.opening_balance,
                "tipo_movimiento": "Credito",
                "fuente": fuente,
                "imputacion": "Saldo Inicial",
            })

        # =========================
        # MOVIMIENTOS
        # =========================
        for tx in result.transactions:
            rows.append({
                "fecha": tx.date,
                "descripcion": tx.description,
                "importe": tx.amount,
                "saldo": tx.balance,
                "tipo_movimiento": "Credito" if tx.amount > 0 else "Debito",
                "fuente": fuente,
                "imputacion": cls._map_imputacion(tx.description),
            })

        df = pd.DataFrame(
            rows,
            columns=[
                "fecha",
                "descripcion",
                "importe",
                "saldo",
                "tipo_movimiento",
                "fuente",
                "imputacion",
            ],
        )

        # =========================
        # NOMBRE ARCHIVO
        # =========================
        bank = (
            result.meta.bank_name.replace(" ", "_").lower()
            if result.meta and result.meta.bank_name
            else "banco"
        )

        filename = (
            f"{datetime.now().year}-{datetime.now().month:02d}_"
            f"extractos_{bank}_v2.xlsx"
        )

        output_path = os.path.join(output_folder, filename)

        # =========================
        # ESCRITURA EXCEL (SIN FORMATO EXTRA)
        # =========================
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="extracto")

            workbook = writer.book
            worksheet = writer.sheets["extracto"]

            worksheet.set_column("A:A", 12)  # fecha
            worksheet.set_column("B:B", 45)  # descripcion
            worksheet.set_column("C:D", 16)  # importe / saldo
            worksheet.set_column("E:E", 14)  # tipo_movimiento
            worksheet.set_column("F:F", 28)  # fuente
            worksheet.set_column("G:G", 30)  # imputacion

            worksheet.freeze_panes("A2")

        return output_path
