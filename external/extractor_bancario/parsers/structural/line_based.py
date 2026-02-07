# parsers/structural/line_based.py

import io
import re
import pdfplumber
from datetime import datetime
from typing import Any, List

from core.models import (
    DocumentProfile,
    Transaction,
    StatementMeta,
    WarningItem,
)
from parsers.structural.base import BaseStructuralParser


DATE_REGEX = re.compile(r"\b(\d{2}/\d{2}/\d{2,4})\b")
AMOUNT_REGEX = re.compile(r"-?\$?\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})")


def parse_date(date_str: str):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue
    return None


def parse_amount(amount_str: str):
    try:
        cleaned = (
            amount_str.replace("$", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", ".")
        )
        return float(cleaned)
    except Exception:
        return None


class LineBasedParser(BaseStructuralParser):
    name = "LINE_BASED"

    def detect(self, profile: DocumentProfile) -> float:
        if not profile.is_text_pdf or not profile.sample_text:
            return 0.0

        date_hits = len(DATE_REGEX.findall(profile.sample_text))
        return min(date_hits / 3, 1.0)

    def extract(self, pdf_bytes: bytes, profile: DocumentProfile) -> Any:
        lines = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue

                for raw_line in text.split("\n"):
                    clean = raw_line.strip()
                    if clean:
                        lines.append(
                            {
                                "text": clean,
                                "page": page_idx + 1,
                            }
                        )

        return lines

    def normalize(self, raw_data: Any, profile: DocumentProfile) -> List[Transaction]:
        transactions: List[Transaction] = []
        current = None

        for row in raw_data:
            text = row["text"]
            page = row["page"]

            date_match = DATE_REGEX.search(text)
            amounts = AMOUNT_REGEX.findall(text)

            if date_match and len(amounts) >= 1:
                if current:
                    transactions.append(current)

                tx_date = parse_date(date_match.group(1))

                # Si hay 2 importes: movimiento + saldo
                if len(amounts) >= 2:
                    amount = parse_amount(amounts[-2])
                    balance = parse_amount(amounts[-1])
                else:
                    amount = parse_amount(amounts[-1])
                    balance = None

                description = text
                description = DATE_REGEX.sub("", description)
                for amt in amounts:
                    description = description.replace(amt, "")
                description = description.strip(" -")

                current = Transaction(
                    date=tx_date,
                    description=description,
                    amount=amount,
                    balance=balance,
                    source_page=page,
                    source_raw=text,
                )

            elif current:
                current.description += " " + text

        if current:
            transactions.append(current)

        return transactions

    def extract_meta(self, raw_data: Any, profile: DocumentProfile) -> StatementMeta:
        return StatementMeta()

    def validate(
        self,
        transactions: List[Transaction],
        meta: StatementMeta,
    ) -> List[WarningItem]:

        warnings: List[WarningItem] = []

        if not transactions:
            warnings.append(
                WarningItem(
                    code="NO_TRANSACTIONS",
                    severity="CRITICAL",
                    message="No se detectaron movimientos",
                )
            )
            return warnings

        no_balance = [t for t in transactions if t.balance is None]
        if no_balance:
            warnings.append(
                WarningItem(
                    code="MISSING_BALANCE",
                    severity="MED",
                    message=f"{len(no_balance)} movimientos sin saldo detectado",
                )
            )

        return warnings

