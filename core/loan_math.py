from decimal import Decimal, ROUND_HALF_UP


TWO_DECIMALS = Decimal("0.01")


def _to_decimal(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def calculate_flat_loan_metrics(principal, rate_percent, periods):
    principal_value = _to_decimal(principal)
    rate_value = _to_decimal(rate_percent)
    periods_value = max(int(periods or 0), 0)

    if periods_value <= 0:
        return {
            "principal": principal_value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
            "rate_percent": rate_value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
            "periods": 0,
            "interest_per_period": Decimal("0.00"),
            "total_interest": Decimal("0.00"),
            "total_to_repay": principal_value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
            "suggested_payment_per_period": Decimal("0.00"),
        }

    interest_per_period = (principal_value * rate_value) / Decimal("100")
    total_interest = (interest_per_period * periods_value).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
    total_to_repay = (principal_value + total_interest).quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)
    suggested_payment = (total_to_repay / Decimal(periods_value)).quantize(
        TWO_DECIMALS,
        rounding=ROUND_HALF_UP,
    )

    return {
        "principal": principal_value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
        "rate_percent": rate_value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
        "periods": periods_value,
        "interest_per_period": interest_per_period.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP),
        "total_interest": total_interest,
        "total_to_repay": total_to_repay,
        "suggested_payment_per_period": suggested_payment,
    }
