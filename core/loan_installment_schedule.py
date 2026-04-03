from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.loan_math import calculate_flat_loan_metrics
from core.loan_repayment_logic import add_period, quantize_money


def _get_repayment_value(repayment, attr_name, default=None):
    if isinstance(repayment, dict):
        return repayment.get(attr_name, default)

    return getattr(repayment, attr_name, default)


def _resolve_first_due_date(loan) -> date | None:
    if getattr(loan, "first_payment_date", None):
        return loan.first_payment_date

    if getattr(loan, "release_date", None):
        return add_period(loan.release_date, getattr(loan, "period_type", "monthly"), 1)

    return None


def build_loan_installment_schedule(loan, repayments):
    metrics = calculate_flat_loan_metrics(
        loan.principal_amount,
        getattr(loan.interest_type, "rate", Decimal("0")) or Decimal("0"),
        loan.term_periods,
    )

    base_payment = quantize_money(
        getattr(loan, "payment_per_period", None) or metrics["suggested_payment_per_period"]
    )
    due_base = _resolve_first_due_date(loan)
    remaining_total_contract = quantize_money(metrics["total_to_repay"])
    remaining_principal_contract = quantize_money(metrics["principal"])

    rows = []
    for installment_number in range(1, metrics["periods"] + 1):
        if remaining_total_contract <= Decimal("0.00"):
            break

        expected_payment = (
            remaining_total_contract
            if installment_number == metrics["periods"] or remaining_total_contract <= base_payment
            else base_payment
        )
        expected_payment = quantize_money(expected_payment)
        expected_interest = quantize_money(metrics["interest_per_period"])
        expected_principal = min(
            remaining_principal_contract,
            max(expected_payment - expected_interest, Decimal("0.00")),
        )
        expected_principal = quantize_money(expected_principal)

        rows.append({
            "installment_number": installment_number,
            "installment_label": (
                f"Dia {installment_number}"
                if getattr(loan, "period_type", "monthly") == "daily"
                else f"Mês {installment_number}"
            ),
            "due_date": add_period(due_base, getattr(loan, "period_type", "monthly"), installment_number - 1)
                if due_base else None,
            "expected_payment": expected_payment,
            "expected_interest": expected_interest,
            "expected_principal": expected_principal,
            "paid_total": Decimal("0.00"),
            "paid_interest": Decimal("0.00"),
            "paid_principal": Decimal("0.00"),
            "remaining_total": expected_payment,
            "remaining_interest": expected_interest,
            "remaining_principal_component": expected_principal,
            "last_payment_date": None,
        })

        remaining_total_contract = quantize_money(remaining_total_contract - expected_payment)
        remaining_principal_contract = quantize_money(
            max(remaining_principal_contract - expected_principal, Decimal("0.00"))
        )

    current_row_index = 0
    for repayment in sorted(
        list(repayments),
        key=lambda item: (
            _get_repayment_value(item, "payment_date"),
            _get_repayment_value(item, "id", 0),
        ),
    ):
        remaining_amount = quantize_money(_get_repayment_value(repayment, "amount", Decimal("0.00")))
        payment_date = _get_repayment_value(repayment, "payment_date")

        while remaining_amount > 0 and current_row_index < len(rows):
            row = rows[current_row_index]

            if row["remaining_total"] <= Decimal("0.00"):
                current_row_index += 1
                continue

            allocated = Decimal("0.00")

            if row["remaining_interest"] > Decimal("0.00"):
                interest_piece = min(remaining_amount, row["remaining_interest"])
                interest_piece = quantize_money(interest_piece)
                row["paid_interest"] = quantize_money(row["paid_interest"] + interest_piece)
                row["remaining_interest"] = quantize_money(
                    max(row["remaining_interest"] - interest_piece, Decimal("0.00"))
                )
                remaining_amount = quantize_money(remaining_amount - interest_piece)
                allocated += interest_piece

            if remaining_amount > Decimal("0.00") and row["remaining_principal_component"] > Decimal("0.00"):
                principal_piece = min(remaining_amount, row["remaining_principal_component"])
                principal_piece = quantize_money(principal_piece)
                row["paid_principal"] = quantize_money(row["paid_principal"] + principal_piece)
                row["remaining_principal_component"] = quantize_money(
                    max(row["remaining_principal_component"] - principal_piece, Decimal("0.00"))
                )
                remaining_amount = quantize_money(remaining_amount - principal_piece)
                allocated += principal_piece

            if allocated > Decimal("0.00"):
                row["paid_total"] = quantize_money(row["paid_total"] + allocated)
                row["remaining_total"] = quantize_money(
                    max(row["expected_payment"] - row["paid_total"], Decimal("0.00"))
                )
                row["last_payment_date"] = payment_date

            if row["remaining_total"] <= Decimal("0.00"):
                current_row_index += 1

            if allocated <= Decimal("0.00"):
                break

    active_installment = None
    for row in rows:
        row["is_paid"] = row["remaining_total"] <= Decimal("0.00")
        if not row["is_paid"] and active_installment is None:
            active_installment = row

    for row in rows:
        row["is_active"] = active_installment is not None and row["installment_number"] == active_installment["installment_number"]
        row["is_partial"] = row["paid_total"] > Decimal("0.00") and row["remaining_total"] > Decimal("0.00")
        row["is_locked"] = not row["is_paid"] and not row["is_active"]
        if row["is_paid"]:
            row["status"] = "paid"
            row["status_label"] = "Pago"
        elif row["is_active"] and row["is_partial"]:
            row["status"] = "partial"
            row["status_label"] = "Parcial"
        elif row["is_active"]:
            row["status"] = "current"
            row["status_label"] = "Actual"
        else:
            row["status"] = "locked"
            row["status_label"] = "Bloqueado"

    summary = {
        "remaining_total": quantize_money(sum((row["remaining_total"] for row in rows), Decimal("0.00"))),
        "remaining_principal": quantize_money(
            sum((row["remaining_principal_component"] for row in rows), Decimal("0.00"))
        ),
        "active_installment": active_installment,
        "completed_installments": sum(1 for row in rows if row["is_paid"]),
        "total_installments": len(rows),
    }

    return metrics, rows, summary


def allocate_amount_to_installments(schedule_rows, amount):
    remaining_amount = quantize_money(amount)
    total_interest = Decimal("0.00")
    total_principal = Decimal("0.00")
    touched_installments = []

    for row in schedule_rows:
        if remaining_amount <= Decimal("0.00"):
            break

        row_interest_remaining = quantize_money(row.get("remaining_interest", Decimal("0.00")))
        row_principal_remaining = quantize_money(row.get("remaining_principal_component", Decimal("0.00")))

        allocated_to_row = Decimal("0.00")

        if row_interest_remaining > Decimal("0.00"):
            interest_piece = min(remaining_amount, row_interest_remaining)
            interest_piece = quantize_money(interest_piece)
            total_interest = quantize_money(total_interest + interest_piece)
            remaining_amount = quantize_money(remaining_amount - interest_piece)
            allocated_to_row += interest_piece

        if remaining_amount > Decimal("0.00") and row_principal_remaining > Decimal("0.00"):
            principal_piece = min(remaining_amount, row_principal_remaining)
            principal_piece = quantize_money(principal_piece)
            total_principal = quantize_money(total_principal + principal_piece)
            remaining_amount = quantize_money(remaining_amount - principal_piece)
            allocated_to_row += principal_piece

        if allocated_to_row > Decimal("0.00"):
            touched_installments.append(row["installment_number"])

    total_applied = quantize_money(total_interest + total_principal)
    return {
        "interest_amount": total_interest,
        "principal_amount": total_principal,
        "total_applied": total_applied,
        "unallocated_amount": remaining_amount,
        "touched_installments": touched_installments,
    }
