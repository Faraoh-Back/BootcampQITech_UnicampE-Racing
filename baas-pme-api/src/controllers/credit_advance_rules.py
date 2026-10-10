from errors import NonPositiveCreditAdvance


def ensure_positive_credit_advance_net(gross_amount: int, fee_amount: int) -> None:
    """Uma nova antecipação precisa gerar liquidez, independentemente do saldo."""
    if gross_amount - fee_amount <= 0:
        raise NonPositiveCreditAdvance()
