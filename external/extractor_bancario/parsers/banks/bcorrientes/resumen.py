import re
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import pdfplumber

from parsers.structural.base import BaseStructuralParser
from core.models import Transaction, StatementMeta, WarningItem


class ResumenBancoCorrientesParser(BaseStructuralParser):

    name = "RESUMEN_BANCO_CORRIENTES"
    bank_code = "bcorrientes"

    # =====================================================
    # DETECCIÓN
    # =====================================================
    def detect(self, profile) -> float:
        if not profile.is_text_pdf:
            return 0.0
        text = (profile.sample_text or "").lower()
        if "banco de corrientes" in text or "banco de la pcia de corrientes" in text:
            return 1.0
        return 0.0

    # =====================================================
    # EXTRACCIÓN RAW
    # =====================================================
    def extract(self, pdf_bytes: bytes, profile) -> Dict[str, Any]:
        text_pages: List[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text_pages.append(page.extract_text() or "")
        
        return {
            "full_text": "\n".join(text_pages),
            "pages": text_pages
        }

    # =====================================================
    # METADATA
    # =====================================================
    def extract_meta(self, raw: Dict[str, Any], profile) -> StatementMeta:
        text = raw.get("full_text", "")
        meta = StatementMeta(
            bank_name="Banco de Corrientes",
            account_type="Caja de Ahorro",
            currency="ARS",
        )

        m_per = re.search(r"Periodo\s*:\s*(\d{2}/\d{2}/\d{2})\s*al\s*(\d{2}/\d{2}/\d{2})", text, re.I)
        if m_per:
            meta.period_start = datetime.strptime(m_per.group(1), "%d/%m/%y").date()
            meta.period_end = datetime.strptime(m_per.group(2), "%d/%m/%y").date()

        m_ini = re.search(r"SALDO INICIAL\s*([\d.,]+)", text, re.I)
        if m_ini: meta.opening_balance = self._parse_amount(m_ini.group(1))

        m_fin = re.search(r"SALDO FINAL\s*([\d.,]+)", text, re.I)
        if m_fin: meta.closing_balance = self._parse_amount(m_fin.group(1))

        return meta

    # =====================================================
    # NORMALIZACIÓN (Con Filtro de Secciones)
    # =====================================================
    def normalize(self, raw: Dict[str, Any], profile) -> List[Transaction]:
        transactions: List[Transaction] = []
        meta = self.extract_meta(raw, profile)
        running_balance = meta.opening_balance
        
        # Regex estricto para montos con decimales
        money_pattern = re.compile(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")

        for p_idx, page_text in enumerate(raw.get("pages", []), 1):
            # CORTAMOS la página si llegamos a secciones de totales o transferencias MEP
            # Esto evita duplicados de tablas informativas al final del PDF
            useful_text = re.split(r"TRANSFERENCIAS MEP|DEBITOS AUTOMATICOS", page_text, flags=re.I)[0]
            
            lines = useful_text.split('\n')
            for line in lines:
                line = line.strip()
                
                # Regla: Debe empezar con fecha
                if not re.match(r"^\d{2}/\d{2}/\d{2}", line):
                    continue
                
                if "saldo final" in line.lower() or "saldo inicial" in line.lower():
                    continue

                date_str = line[:8]
                content = line[8:].strip()
                
                # Buscamos montos. En la tabla principal siempre hay al menos 2 (Mov + Saldo)
                money_found = money_pattern.findall(content)
                
                if len(money_found) >= 1:
                    try:
                        tx_date = datetime.strptime(date_str, "%d/%m/%y").date()
                        row_balance = self._parse_amount(money_found[-1])
                        
                        # Cálculo contable por diferencia
                        if running_balance is not None:
                            amount = round(row_balance - running_balance, 2)
                        else:
                            # Si es la primera, el movimiento es el penúltimo o el saldo mismo
                            amount = self._parse_amount(money_found[-2]) if len(money_found) > 1 else 0.0

                        # Evitamos ruidos de líneas que no cambian el saldo (metadata interna)
                        if amount == 0 and len(money_found) < 2:
                            continue

                        # Limpieza de descripción
                        desc = content
                        for m in money_found:
                            desc = desc.replace(m, "")
                        desc = re.sub(r"\s+", " ", desc).strip()

                        transactions.append(Transaction(
                            date=tx_date,
                            description=desc,
                            amount=amount,
                            balance=row_balance,
                            currency="ARS",
                            type_hint="CREDIT" if amount > 0 else "DEBIT",
                            source_page=p_idx,
                            source_raw=line
                        ))
                        
                        running_balance = row_balance
                    except:
                        continue

        return transactions

    def _parse_amount(self, raw: str) -> float:
        if not raw: return 0.0
        s = raw.strip().replace("$", "").replace(" ", "")
        try:
            if "," in s and "." in s:
                if s.rfind(",") > s.rfind("."): s = s.replace(".", "").replace(",", ".")
                else: s = s.replace(",", "")
            elif "," in s:
                s = s.replace(",", ".")
            return float(s)
        except:
            return 0.0

    def validate(self, transactions: List[Transaction], meta: StatementMeta):
        warnings: List[WarningItem] = []
        if not transactions:
            warnings.append(WarningItem(code="NO_TRANSACTIONS", severity="CRITICAL", message="No se detectaron movimientos."))
        elif meta.closing_balance is not None:
            diff = abs(transactions[-1].balance - meta.closing_balance)
            if diff > 0.01:
                warnings.append(WarningItem(
                    code="BALANCE_MISMATCH", 
                    severity="HIGH", 
                    message=f"Discrepancia contable. Esperado: {meta.closing_balance}, Calculado: {transactions[-1].balance}"
                ))
        return warnings