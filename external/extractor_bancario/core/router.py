from typing import List

from core.models import ExtractionResult, WarningItem
from core.validation import validate_balance_consistency

from parsers.structural.base import BaseStructuralParser
from bank_detection.detector import BankDetector


class ParserRouter:

    def __init__(self, structural_parsers: List[BaseStructuralParser]):
        self.structural_parsers = structural_parsers

    def route(self, pdf_bytes: bytes, profile) -> ExtractionResult:
        warnings = []
        trace = []

        # =====================================================
        # 1. DETECCIÓN DE BANCO
        # =====================================================
        bank_code = BankDetector.detect(profile)

        if not bank_code:
            return ExtractionResult(
                profile=profile,
                transactions=[],
                meta=None,
                warnings=[
                    WarningItem(
                        code="BANK_NOT_DETECTED",
                        severity="CRITICAL",
                        message="No se pudo detectar el banco del documento",
                    )
                ],
                confidence_score=0,
                parser_trace=["BANK_DETECTION_FAILED"],
            )

        trace.append(f"BANK:{bank_code}")

        # =====================================================
        # 2. FILTRAR PARSERS POR BANCO
        # =====================================================
        eligible_parsers = [
            p for p in self.structural_parsers
            if getattr(p, "bank_code", None) == bank_code
        ]

        if not eligible_parsers:
            return ExtractionResult(
                profile=profile,
                transactions=[],
                meta=None,
                warnings=[
                    WarningItem(
                        code="NO_PARSER_FOR_BANK",
                        severity="CRITICAL",
                        message=f"No hay parser registrado para el banco '{bank_code}'",
                    )
                ],
                confidence_score=0,
                parser_trace=trace,
            )

        # =====================================================
        # 3. SCORING DE PARSERS
        # =====================================================
        scored = [
            (parser.detect(profile), parser)
            for parser in eligible_parsers
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        # =====================================================
        # 4. EJECUCIÓN
        # =====================================================
        for score, parser in scored:
            if score <= 0:
                continue

            trace.append(f"TRY:{parser.name}")

            try:
                raw = parser.extract(pdf_bytes, profile)
                transactions = parser.normalize(raw, profile)
                meta = parser.extract_meta(raw, profile)
                local_warnings = parser.validate(transactions, meta)

                balance_warnings = []
                balance_score = 100

                # Validación genérica solo si NO es resumen
                if profile.document_type != "RESUMEN":
                    balance_warnings, balance_score = validate_balance_consistency(
                        transactions
                    )

                all_warnings = local_warnings + balance_warnings
                confidence = int((score * 100 + balance_score) / 2)

                return ExtractionResult(
                    profile=profile,
                    transactions=transactions,
                    meta=meta,
                    warnings=all_warnings,
                    confidence_score=confidence,
                    parser_trace=trace,
                )

            except Exception as e:
                warnings.append(
                    WarningItem(
                        code="PARSER_FAILED",
                        severity="HIGH",
                        message=str(e),
                    )
                )
                trace.append(f"FAIL:{parser.name}")

        # =====================================================
        # 5. FALLBACK
        # =====================================================
        return ExtractionResult(
            profile=profile,
            transactions=[],
            meta=None,
            warnings=warnings,
            confidence_score=0,
            parser_trace=trace,
        )
