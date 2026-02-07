# core/diagnostics.py

import hashlib
import io
from typing import Optional

import pdfplumber

from .models import DocumentProfile



def diagnose_pdf(pdf_bytes: bytes, file_name: str) -> DocumentProfile:
    """
    Analiza el PDF a partir de bytes y construye el perfil del documento.
    Compatible con Streamlit / APIs / tests.
    """

    file_hash = hashlib.md5(pdf_bytes).hexdigest()

    # 👉 usamos BytesIO, NO paths
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)

        text_pages = []
        for page in pdf.pages[:2]:  # sample primeras páginas
            try:
                t = page.extract_text() or ""
                text_pages.append(t)
            except Exception:
                pass

    sample_text = "\n".join(text_pages)

    is_text_pdf = bool(sample_text.strip())
    is_scanned = not is_text_pdf

    profile = DocumentProfile(
        file_name=file_name,
        file_hash=file_hash,
        page_count=page_count,
        is_text_pdf=is_text_pdf,
        is_scanned=is_scanned,
        sample_text=sample_text,
    )

    # ==================================
    # HINTS DE CONTENIDO
    # ==================================

    st = sample_text.lower()

    profile.has_balance_keywords = "saldo" in st
    profile.has_cbu_keywords = "cbu" in st
    profile.has_period_keywords = "periodo" in st or "período" in st

    # ==================================
    # DETECCIÓN TIPO DE DOCUMENTO
    # ==================================

    if (
        "resumen" in st
        and "saldo" in st
        and profile.has_period_keywords
    ):
        profile.document_type = "RESUMEN"
    else:
        profile.document_type = "MOVIMIENTOS"

    return profile

