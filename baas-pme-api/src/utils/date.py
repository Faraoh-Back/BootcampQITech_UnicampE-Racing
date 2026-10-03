from calendar import monthrange
from datetime import date


def add_months(value: date, months: int) -> date:
    """Soma meses preservando o dia quando possível, ou o último dia do mês.

    Exemplo: 31/01 + 1 mês é 28/02 (ou 29/02 em ano bissexto).
    """
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))
