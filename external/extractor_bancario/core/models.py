# core/models.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date


# =========================
# WARNINGS / VALIDACIONES
# =========================

@dataclass
class WarningItem:
    code: str                      # ej: BALANCE_MISMATCH
    severity: str                  # LOW | MED | HIGH | CRITICAL
    message: str
    pages: Optional[List[int]] = None
    evidence: Optional[Dict[str, Any]] = None


# =========================
# DEBUG / AUDITORÍA
# =========================

@dataclass
class DebugBundle:
    raw_text_sample: Optional[str] = None
    raw_rows: Optional[List[Any]] = None
    intermediate_tables: Optional[List[Any]] = None
    timings: Dict[str, float] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)


# =========================
# PERFIL DEL DOCUMENTO
# =========================

@dataclass
class DocumentProfile:
    file_name: str
    file_hash: str
    page_count: int

    is_text_pdf: bool
    is_scanned: bool

    language_hint: str = "es-AR"

    # 👇 NUEVO: tipo de documento
    document_type: str = "UNKNOWN"   # RESUMEN | MOVIMIENTOS | UNKNOWN

    # hints de estructura
    structure_hint: Optional[str] = None
    has_balance_keywords: bool = False
    has_cbu_keywords: bool = False
    has_period_keywords: bool = False

    # detección de banco
    bank_candidates: List[Dict[str, float]] = field(default_factory=list)

    sample_text: Optional[str] = None
    errors: List[str] = field(default_factory=list)


# =========================
# TRANSACCIÓN NORMALIZADA
# =========================

@dataclass
class Transaction:
    date: date
    description: str
    amount: float                  # signed
    balance: Optional[float] = None
    currency: Optional[str] = None

    type_hint: Optional[str] = None        # DEBIT / CREDIT / UNKNOWN
    category_hint: Optional[str] = None    # IMPUESTO / COMISION / TRANSFER / TARJETA

    source_page: Optional[int] = None
    source_raw: Optional[str] = None


# =========================
# METADATA DEL RESUMEN
# =========================

@dataclass
class StatementMeta:
    bank_name: Optional[str] = None
    account_type: Optional[str] = None
    currency: Optional[str] = None

    period_start: Optional[date] = None
    period_end: Optional[date] = None

    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None


# =========================
# RESULTADO FINAL
# =========================

@dataclass
class ExtractionResult:
    profile: DocumentProfile

    transactions: List[Transaction]
    meta: Optional[StatementMeta]

    warnings: List[WarningItem] = field(default_factory=list)
    confidence_score: int = 0

    parser_trace: List[str] = field(default_factory=list)
    debug: Optional[DebugBundle] = None
