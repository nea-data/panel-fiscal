# core/validation.py

from typing import List, Tuple
from core.models import Transaction, WarningItem


def detect_saldo_inicial(transactions: List[Transaction]) -> int:
    """
    Devuelve el índice del Saldo Inicial si existe.
    Heurística:
    - primera transacción
    - descripción contiene 'saldo'
    """
    if not transactions:
        return -1

    first = transactions[0]
    if first.description and "saldo" in first.description.lower():
        return 0

    return -1


def infer_amount_sign(
    prev_balance: float,
    curr_balance: float,
    raw_amount: float,
) -> float:
    """
    Determina el signo correcto del importe
    comparando balances.
    """
    if prev_balance is None or curr_balance is None or raw_amount is None:
        return raw_amount

    delta = curr_balance - prev_balance

    # si coincide en magnitud, usamos el signo del delta
    if abs(abs(delta) - abs(raw_amount)) < 0.02:
        return delta

    return raw_amount


def validate_balance_consistency(
    transactions: List[Transaction],
) -> Tuple[List[WarningItem], int]:
    """
    Valida que el saldo cuadre movimiento a movimiento.
    Devuelve warnings + score de consistencia (0..100)
    """

    warnings: List[WarningItem] = []

    if len(transactions) < 2:
        return warnings, 100

    # ================================
    # 🔑 CLAVE: ordenar cronológicamente
    # ================================
    ordered = sorted(
        enumerate(transactions),
        key=lambda x: (x[1].date, x[0])  # fecha + orden original
    )

    ordered_tx = [t for _, t in ordered]

    ok = 0
    fail = 0

    start_idx = detect_saldo_inicial(ordered_tx)

    for i in range(start_idx + 1, len(ordered_tx)):
        prev = ordered_tx[i - 1]
        curr = ordered_tx[i]

        if prev.balance is None or curr.balance is None:
            continue

        # inferimos signo real
        corrected_amount = infer_amount_sign(
            prev.balance, curr.balance, curr.amount
        )
        curr.amount = corrected_amount

        expected = prev.balance + corrected_amount

        if abs(expected - curr.balance) < 0.02:
            ok += 1
        else:
            fail += 1
            warnings.append(
                WarningItem(
                    code="BALANCE_MISMATCH",
                    severity="HIGH",
                    message=(
                        f"Saldo inconsistente en {curr.date}: "
                        f"esperado {expected:.2f}, obtenido {curr.balance:.2f}"
                    ),
                    pages=[curr.source_page],
                    evidence={
                        "prev_balance": prev.balance,
                        "amount": corrected_amount,
                        "expected": expected,
                        "actual": curr.balance,
                    },
                )
            )

    total = ok + fail
    score = int((ok / total) * 100) if total > 0 else 100

    return warnings, score
