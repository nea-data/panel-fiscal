# parsers/structural/base.py

from abc import ABC, abstractmethod
from typing import Any, List
from core.models import DocumentProfile, Transaction, StatementMeta, WarningItem


class BaseStructuralParser(ABC):
    """
    Parser estructural base.
    NO asume banco.
    NO asume formato fijo.
    """

    name: str = "BASE"

    @abstractmethod
    def detect(self, profile: DocumentProfile) -> float:
        """
        Devuelve un score (0..1) de cuán adecuado es este parser
        para el documento diagnosticado.
        """
        pass

    @abstractmethod
    def extract(self, pdf_bytes: bytes, profile: DocumentProfile) -> Any:
        """
        Extrae información cruda del PDF.
        Puede devolver listas, dicts, tablas intermedias, etc.
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Any, profile: DocumentProfile) -> List[Transaction]:
        """
        Convierte la extracción cruda en transacciones normalizadas.
        """
        pass

    @abstractmethod
    def extract_meta(self, raw_data: Any, profile: DocumentProfile) -> StatementMeta:
        """
        Extrae metadata: banco, período, saldos, moneda, etc.
        """
        pass

    @abstractmethod
    def validate(
        self,
        transactions: List[Transaction],
        meta: StatementMeta
    ) -> List[WarningItem]:
        """
        Ejecuta validaciones propias del parser.
        No rompe, solo genera warnings.
        """
        pass
