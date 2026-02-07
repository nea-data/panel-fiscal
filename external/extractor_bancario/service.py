"""
Servicio principal de extracción bancaria.

Este módulo es el ÚNICO punto de entrada que debe usar el Panel Fiscal.
Se encarga de:
- Diagnosticar el PDF
- Detectar el banco
- Ejecutar el parser correspondiente
- Devolver el resultado normalizado
"""

from typing import Optional

# ======================================================
# IMPORTS INTERNOS (ABSOLUTOS, SIN AMBIGÜEDAD)
# ======================================================

from external.extractor_bancario.bank_detection.detector import BankDetector

from external.extractor_bancario.core.diagnostics import diagnose_pdf
from external.extractor_bancario.core.router import ParserRouter
from external.extractor_bancario.core.models import ExtractionResult

from external.extractor_bancario.parsers.banks.bcorrientes.resumen import (
    ResumenBancoCorrientesParser,
)

# ======================================================
# REGISTRO DE PARSERS POR BANCO
# ======================================================

BANK_PARSERS = {
    "bcorrientes": [
        ResumenBancoCorrientesParser(),
    ],
    # futuros bancos:
    # "bnacion": [ResumenBancoNacionParser()],
}

# ======================================================
# FACTORY DE ROUTER
# ======================================================

def _build_router_for_bank(bank_code: str) -> ParserRouter:
    """
    Construye el router con los parsers correspondientes al banco detectado.
    """
    parsers = BANK_PARSERS.get(bank_code)

    if not parsers:
        raise ValueError(
            f"No hay parsers registrados para el banco '{bank_code}'"
        )

    return ParserRouter(structural_parsers=parsers)

# ======================================================
# API PÚBLICA (LO QUE IMPORTA LA APP)
# ======================================================

def extract_bank_statement(
    pdf_bytes: bytes,
    filename: str,
) -> ExtractionResult:
    """
    Punto de entrada único para el Panel Fiscal.

    :param pdf_bytes: contenido binario del PDF
    :param filename: nombre del archivo (para diagnóstico)
    :return: ExtractionResult
    """

    # 1️⃣ Diagnóstico del PDF
    profile = diagnose_pdf(pdf_bytes, filename)

    # 2️⃣ Detección de banco
    bank_code: Optional[str] = BankDetector.detect(profile)

    if not bank_code:
        raise ValueError(
            "No se pudo detectar el banco del resumen. "
            "El documento no está soportado."
        )

    # 3️⃣ Construcción del router según banco
    router = _build_router_for_bank(bank_code)

    # 4️⃣ Ejecución del extractor
    result: ExtractionResult = router.route(pdf_bytes, profile)

    # 5️⃣ Metadata adicional (útil para el panel)
    result.profile.detected_bank = bank_code

    return result

