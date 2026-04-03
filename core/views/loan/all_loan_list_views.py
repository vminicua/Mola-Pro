# core/views/loans/loan_list_views.py
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.loan_math import calculate_flat_loan_metrics
from core.models import Loan
from django.http import JsonResponse
from django.shortcuts import get_object_or_404





@login_required
def loan_list_all(request):
    """
    Lista TODOS os empréstimos (independentemente do status)
    + KPIs da carteira.
    """
    loans_qs = (
        Loan.objects
        .select_related("member", "loan_type", "interest_type", "approved_by", "company_account")
        .prefetch_related("disbursements")
        .order_by("-created_at")
    )

    loans = list(loans_qs)

    total_loans = len(loans)
    total_principal = Decimal("0")
    total_to_repay = Decimal("0")
    total_interest = Decimal("0")

    status_counts = {
        "pending": 0,
        "approved": 0,
        "disbursed": 0,
        "closed": 0,
        "cancelled": 0,
    }

    for loan in loans:
        metrics = calculate_flat_loan_metrics(
            loan.principal_amount,
            getattr(loan.interest_type, "rate", Decimal("0")) or Decimal("0"),
            loan.term_periods,
        )
        principal = metrics["principal"]
        interest = metrics["total_interest"]
        total_amount = metrics["total_to_repay"]

        loan.total_interest = interest
        loan.total_to_repay = total_amount

        # Último desembolso (se existir)
        last_disb = (
            loan.disbursements.order_by("-disburse_date", "-id").first()
            if hasattr(loan, "disbursements")
            else None
        )
        loan.disbursed_date = last_disb.disburse_date if last_disb else None
        loan.disbursed_amount = last_disb.amount if last_disb else None
        loan.disbursed_company_account = last_disb.company_account if last_disb else None

        total_principal += principal
        total_interest += interest
        total_to_repay += total_amount

        if loan.status in status_counts:
            status_counts[loan.status] += 1

    context = {
        "loans": loans,
        "segment": "loans_all",
        "kpi_total_loans": total_loans,
        "kpi_total_principal": total_principal,
        "kpi_total_interest": total_interest,
        "kpi_total_to_repay": total_to_repay,
        "kpi_status_pending": status_counts["pending"],
        "kpi_status_approved": status_counts["approved"],
        "kpi_status_disbursed": status_counts["disbursed"],
        "kpi_status_closed": status_counts["closed"],
        "kpi_status_cancelled": status_counts["cancelled"],
    }
    return render(request, "loan/loan_list_all.html", context)


#========================================================================================================================
#========================================================================================================================



@login_required
def loan_details_any_status(request, loan_id):
    """
    Devolve detalhes completos de um empréstimo (qualquer status) em JSON
    para alimentar o modal com tabs.
    """
    loan = get_object_or_404(
        Loan.objects.select_related(
            "member",
            "loan_type",
            "interest_type",
            "approved_by",
            "created_by",
        ).prefetch_related(
            "disbursements",
            "disbursements__company_account",
            "loan_guarantors",
            "loan_guarantors__guarantor",
            "guarantees",
            "member__client_accounts",
            "member__client_accounts__account_type",
        ),
        pk=loan_id,
    )  # 👈 SEM filtro de status

    # cálculo juros / total a reembolsar
    metrics = calculate_flat_loan_metrics(
        loan.principal_amount,
        getattr(loan.interest_type, "rate", Decimal("0")) or Decimal("0"),
        loan.term_periods,
    )
    total_to_repay = metrics["total_to_repay"]
    total_interest = metrics["total_interest"]
    payment_per_period = loan.payment_per_period or metrics["suggested_payment_per_period"]

    member = loan.member

    # último desembolso (se existir)
    last_disb = loan.disbursements.order_by("-disburse_date", "-id").first()

    # contas do cliente
    client_accounts_data = []
    for ca in member.client_accounts.filter(is_active=True).select_related("account_type"):
        client_accounts_data.append({
            "id": ca.id,
            "account_type": ca.account_type.get_category_display(),
            "account_type_name": ca.account_type.name,
            "identifier": ca.account_identifier,
            "balance": float(ca.balance),
        })

    # fiadores
    guarantors_data = []
    for g in loan.loan_guarantors.select_related("guarantor"):
        guarantors_data.append({
            "id": g.id,
            "name": str(g.guarantor),
            "phone": g.guarantor.phone,
            "account_number": g.account_number,
            "amount": float(g.amount) if g.amount is not None else None,
        })

    # garantias
    guarantees_data = []
    for gg in loan.guarantees.all():
        guarantees_data.append({
            "id": gg.id,
            "name": gg.name,
            "guarantee_type": gg.guarantee_type,
            "serial_number": gg.serial_number,
            "estimated_price": float(gg.estimated_price) if gg.estimated_price is not None else None,
            "description": gg.description,
            "attachment_url": gg.attachment.url if gg.attachment else None,
        })

    data = {
        "loan": {
            "id": loan.id,
            "status": loan.status,
            "loan_type": loan.loan_type.name if loan.loan_type else None,
            "interest_type": loan.interest_type.name if loan.interest_type else None,
            "principal_amount": float(loan.principal_amount),
            "term_periods": loan.term_periods,
            "period_type": loan.period_type,
            "payment_per_period": float(payment_per_period) if payment_per_period is not None else None,
            "total_to_repay": float(total_to_repay),
            "total_interest": float(total_interest),
            "release_date": loan.release_date.isoformat() if loan.release_date else None,
            "first_payment_date": loan.first_payment_date.isoformat() if loan.first_payment_date else None,
            "disburse_method": loan.disburse_method,
            "purpose": loan.purpose,
            "remarks": loan.remarks,
            "created_at": loan.created_at.isoformat() if loan.created_at else None,
            "created_by": loan.created_by.get_full_name() if loan.created_by else None,
            "approved_by": loan.approved_by.get_full_name() if loan.approved_by else None,
        },
        "member": {
            "id": member.id,
            "name": str(member),
            "phone": member.phone,
            "alt_phone": member.alt_phone,
            "email": member.email,
            "city": member.city,
            "address": member.address,
            "profession": member.profession,
            "manager": member.manager.get_full_name() if member.manager else None,
        },
        "disbursement": {
            "exists": last_disb is not None,
            "amount": float(last_disb.amount) if last_disb else None,
            "date": last_disb.disburse_date.isoformat() if last_disb else None,
            "method": last_disb.method if last_disb else None,
            "company_account": last_disb.company_account.name if last_disb and last_disb.company_account else None,
            "company_account_identifier": (
                last_disb.company_account.account_identifier
                if last_disb and last_disb.company_account else None
            ),
            "attachment_url": last_disb.attachment.url if last_disb and last_disb.attachment else None,
            "notes": last_disb.notes if last_disb else None,
        },
        "client_accounts": client_accounts_data,
        "guarantors": guarantors_data,
        "guarantees": guarantees_data,
    }

    return JsonResponse(data, safe=False)
