from typing import Optional


class BankDetector:
    """
    Detecta el banco a partir del contenido del documento.
    Devuelve un identificador interno de banco (string).
    """

    @staticmethod
    def detect(profile, raw: dict | None = None) -> Optional[str]:
        """
        :param profile: resultado de diagnose_pdf
        :param raw: extracción preliminar si existiera (opcional)
        :return: codigo de banco (ej: 'bcorrientes') o None
        """

        text = (profile.sample_text or "").lower()

        # ===============================
        # BANCO DE CORRIENTES
        # ===============================
        if (
            "banco de corrientes" in text
            or "banco de la pcia de corrientes" in text
        ):
            return "bcorrientes"

        # ===============================
        # FUTUROS BANCOS
        # ===============================
        # if "banco de la nacion argentina" in text:
        #     return "bnacion"

        return None
