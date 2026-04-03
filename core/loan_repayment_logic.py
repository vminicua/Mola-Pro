from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


TWO_DECIMALS = Decimal("0.01")


def quantize_money(value) -> Decimal:
    if value in (None, ""):
        value = Decimal("0")

    if not isinstance(value, Decimal):
        value = Decimal(str(value))

    return value.quantize(TWO_DECIMALS, rounding=ROUND_HALF_UP)


def _add_months(base_date: date, months: int = 1) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def add_period(base_date: date | None, period_type: str, steps: int = 1) -> date | None:
    if not base_date:
        return None

    steps_value = max(int(steps or 0), 0)
    if period_type == "daily":
        return base_date + timedelta(days=steps_value)

    return _add_months(base_date, steps_value)


@dataclass(frozen=True)
class RepaymentAllocation:
    interest_amount: Decimal
    principal_amount: Decimal
    principal_balance_after: Decimal
    total_due_now: Decimal


class RepaymentAllocationError(ValueError):
    def __init__(self, code: str, **context) -> None:
        self.code = code
        self.context = context
        super().__init__(code)


def allocate_repayment(
    amount,
    interest_remaining,
    outstanding_principal,
    repayment_type: str,
) -> RepaymentAllocation:
    normalized_type = repayment_type if repayment_type in {"interest_only", "full", "partial"} else "partial"
    amount_value = quantize_money(amount)
    interest_remaining_value = max(quantize_money(interest_remaining), Decimal("0.00"))
    outstanding_principal_value = max(quantize_money(outstanding_principal), Decimal("0.00"))
    total_due_now = quantize_money(interest_remaining_value + outstanding_principal_value)

    if normalized_type == "interest_only":
        if interest_remaining_value <= 0:
            raise RepaymentAllocationError("no_interest_due", interest_remaining=interest_remaining_value)

        if amount_value != interest_remaining_value:
            raise RepaymentAllocationError(
                "interest_only_exact_amount",
                expected=interest_remaining_value,
                actual=amount_value,
            )

        return RepaymentAllocation(
            interest_amount=interest_remaining_value,
            principal_amount=Decimal("0.00"),
            principal_balance_after=outstanding_principal_value,
            total_due_now=total_due_now,
        )

    if normalized_type == "full":
        if amount_value != total_due_now:
            raise RepaymentAllocationError(
                "full_exact_amount",
                expected=total_due_now,
                actual=amount_value,
            )

        return RepaymentAllocation(
            interest_amount=interest_remaining_value,
            principal_amount=outstanding_principal_value,
            principal_balance_after=Decimal("0.00"),
            total_due_now=total_due_now,
        )

    if total_due_now <= 0:
        raise RepaymentAllocationError("no_balance_due", total_due_now=total_due_now)

    if amount_value >= total_due_now:
        raise RepaymentAllocationError(
            "partial_must_be_less_than_total_due",
            total_due_now=total_due_now,
            actual=amount_value,
        )

    if interest_remaining_value > 0 and amount_value <= interest_remaining_value:
        raise RepaymentAllocationError(
            "partial_must_reduce_principal",
            interest_remaining=interest_remaining_value,
            actual=amount_value,
        )

    interest_amount = min(amount_value, interest_remaining_value)
    principal_amount = quantize_money(amount_value - interest_amount)
    principal_balance_after = quantize_money(
        max(outstanding_principal_value - principal_amount, Decimal("0.00"))
    )

    return RepaymentAllocation(
        interest_amount=interest_amount,
        principal_amount=principal_amount,
        principal_balance_after=principal_balance_after,
        total_due_now=total_due_now,
    )
