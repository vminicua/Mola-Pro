from django.shortcuts import render
import json
from datetime import date, timedelta
from decimal import Decimal

from django.db.models.functions import Coalesce, TruncMonth
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models import (
    Sum,
    Count,
    F,
    DecimalField,
    OuterRef,
    Subquery,
    ExpressionWrapper,
)

from core.models import (
    Loan,
    LoanRepayment,
    LoanDisbursement,
    LoanPaymentRequest,
    CompanyAccount,
)


#=============================================================================
#=============================================================================


def _get_last_6_months():
    """
    Devolve uma lista de datas (1º dia de cada mês) dos últimos 6 meses,
    incluindo o mês actual, em ordem cronológica.
    """
    today = timezone.localdate()
    year = today.year
    month = today.month
    months = []

    # Começa no mês actual e recua 5 meses
    for _ in range(6):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    months.reverse()
    return months


#=============================================================================
#=============================================================================


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    start_30d = today - timedelta(days=30)

    # ==========================
    # KPI 1 – Carteira total (somatório do principal de todos empréstimos não cancelados)
    # ==========================
    portfolio_total = (
        Loan.objects.exclude(status="cancelled")
        .aggregate(
            total=Coalesce(
                Sum("principal_amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    # ==========================
    # KPI 2 – Principal em dívida + nº de empréstimos activos
    # ==========================
    active_statuses = ["approved", "disbursed"]
    active_loans_qs = Loan.objects.filter(status__in=active_statuses)

    # Subquery: último principal_balance_after por empréstimo
    last_repayment_sub = (
        LoanRepayment.objects.filter(loan_id=OuterRef("pk"))
        .order_by("-payment_date", "-id")
        .values("principal_balance_after")[:1]
    )

    active_loans_with_outstanding = active_loans_qs.annotate(
        last_balance=Subquery(last_repayment_sub),
        outstanding=Coalesce(
            F("last_balance"),
            F("principal_amount"),
            output_field=DecimalField(max_digits=15, decimal_places=2),
        ),
    )

    outstanding_principal = (
        active_loans_with_outstanding.aggregate(
            total=Coalesce(
                Sum("outstanding"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    outstanding_loans_count = active_loans_qs.count()

    # ==========================
    # KPI 3 – Juros a receber (aproximação: total a pagar - principal)
    # ==========================
    interest_expr = ExpressionWrapper(
        Coalesce(F("payment_per_period"), 0) * Coalesce(F("term_periods"), 0)
        - F("principal_amount"),
        output_field=DecimalField(max_digits=15, decimal_places=2),
    )

    interest_to_receive = (
        active_loans_qs.annotate(interest_total=interest_expr).aggregate(
            total=Coalesce(
                Sum("interest_total"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    # ==========================
    # KPI 4 – Reembolsos hoje
    # ==========================
    today_repayments_qs = LoanRepayment.objects.filter(payment_date=today)

    today_repayments_amount = (
        today_repayments_qs.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )
    today_repayments_count = today_repayments_qs.count()

    # ==========================
    # KPI 5 – Empréstimos pendentes
    # ==========================
    pending_loans_count = Loan.objects.filter(status="pending").count()

    # ==========================
    # KPI 6 – Saldo total das contas da empresa
    # ==========================
    company_accounts_balance = (
        CompanyAccount.objects.filter(is_active=True).aggregate(
            total=Coalesce(
                Sum("balance"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    # ==========================
    # Indicador de variação da carteira (desembolsos mês actual vs anterior)
    # ==========================
    start_month = date(today.year, today.month, 1)
    this_month_start = start_month
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    this_month_disb = (
        LoanDisbursement.objects.filter(
            disburse_date__gte=this_month_start,
            disburse_date__lt=next_month_start,
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    if this_month_start.month == 1:
        prev_month_start = date(this_month_start.year - 1, 12, 1)
    else:
        prev_month_start = date(this_month_start.year, this_month_start.month - 1, 1)

    prev_month_end = this_month_start

    prev_month_disb = (
        LoanDisbursement.objects.filter(
            disburse_date__gte=prev_month_start,
            disburse_date__lt=prev_month_end,
        ).aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )["total"]
        or Decimal("0")
    )

    if prev_month_disb > 0:
        change = (float(this_month_disb) - float(prev_month_disb)) / float(
            prev_month_disb
        ) * 100.0
        kpi_portfolio_change_label = _("{change:+.1f}% vs mês anterior").format(change=change)
    else:
        kpi_portfolio_change_label = _("— vs mês anterior")

    # ==========================
    # Empréstimos recentes
    # ==========================
    recent_loans = (
        Loan.objects.select_related("member")
        .order_by("-created_at")[:8]
    )

    # ==========================
    # Entradas recentes (Reembolsos)
    # ==========================
    recent_cash_items = []

    repay_qs = (
        LoanRepayment.objects.select_related("loan", "member")
        .filter(payment_date__gte=start_30d)
        .order_by("-payment_date")[:20]
    )
    for r in repay_qs:
        recent_cash_items.append(
            {
                "source_type": "loan_repayment",
                "label": _("Reembolso Loan #{loan_id} · {member_name}").format(
                    loan_id=r.loan_id,
                    member_name=f"{r.member.first_name} {r.member.last_name}",
                ),
                "amount": r.amount,
                "tx_date": r.payment_date,
            }
        )

    # Ordenar por data desc e limitar a 10
    recent_cash_items.sort(key=lambda x: x["tx_date"], reverse=True)
    recent_cash_in = recent_cash_items[:10]

    # ==========================
    # Próximos vencimentos (LoanPaymentRequest pendentes)
    # ==========================
    upcoming_qs = (
        LoanPaymentRequest.objects.select_related("loan", "member")
        .filter(status="pending")
        .order_by("due_date")[:20]
    )

    upcoming_due_loans = []
    for pr in upcoming_qs:
        days_to_due = (pr.due_date - today).days
        upcoming_due_loans.append(
            {
                "id": pr.loan_id,
                "member": pr.member,
                "next_due_date": pr.due_date,
                "days_to_due": days_to_due,
            }
        )

    # Gráfico 1: Linha – Desembolsos vs Reembolsos (últimos 6 meses)
    # ==========================
    months = _get_last_6_months()

    disb_by_month = (
        LoanDisbursement.objects.filter(disburse_date__gte=months[0])
        .annotate(m=TruncMonth("disburse_date"))
        .values("m")
        .annotate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )
    )
    disb_map = {row["m"]: row["total"] for row in disb_by_month}

    repay_by_month = (
        LoanRepayment.objects.filter(payment_date__gte=months[0])
        .annotate(m=TruncMonth("payment_date"))
        .values("m")
        .annotate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            )
        )
    )
    repay_map = {row["m"]: row["total"] for row in repay_by_month}

    chart_loan_cashflow_labels = [m.strftime("%b/%Y") for m in months]
    chart_loan_cashflow_disbursed = [float(disb_map.get(m, 0)) for m in months]
    chart_loan_cashflow_repaid = [float(repay_map.get(m, 0)) for m in months]

    # ==========================
    # Gráfico 2: Doughnut – carteira por status
    # ==========================
    status_counts = (
        Loan.objects.values("status")
        .annotate(total=Count("id"))
    )
    status_map = {row["status"]: row["total"] for row in status_counts}

    status_active_count = status_map.get("disbursed", 0) + status_map.get(
        "approved", 0
    )
    status_pending_count = status_map.get("pending", 0)
    status_closed_count = status_map.get("closed", 0)
    status_cancelled_count = status_map.get("cancelled", 0)

    chart_loan_status_labels = [
        _("Activos"),
        _("Pendentes"),
        _("Fechados"),
        _("Cancelados"),
    ]
    chart_loan_status_values = [
        status_active_count,
        status_pending_count,
        status_closed_count,
        status_cancelled_count,
    ]

    # Contexto final
    # ==========================
    context = {
        "page_title": "Mola Pro",
        "segment": "dashboard",

        # KPIs
        "kpi_portfolio_total": portfolio_total,
        "kpi_portfolio_change_label": kpi_portfolio_change_label,
        "kpi_outstanding_principal": outstanding_principal,
        "kpi_outstanding_loans_count": outstanding_loans_count,
        "kpi_interest_to_receive": interest_to_receive,
        "kpi_today_repayments": today_repayments_amount,
        "kpi_today_repayments_count": today_repayments_count,
        "kpi_pending_loans_count": pending_loans_count,
        "kpi_company_accounts_balance": company_accounts_balance,
        "kpi_status_active_count": status_active_count,
        "kpi_status_pending_count": status_pending_count,
        "kpi_status_closed_count": status_closed_count,
        "kpi_status_cancelled_count": status_cancelled_count,

        # Listas
        "recent_loans": recent_loans,
        "recent_cash_in": recent_cash_in,
        "upcoming_due_loans": upcoming_due_loans,

        # Gráficos
        "chart_loan_cashflow_labels": json.dumps(chart_loan_cashflow_labels),
        "chart_loan_cashflow_disbursed": json.dumps(chart_loan_cashflow_disbursed),
        "chart_loan_cashflow_repaid": json.dumps(chart_loan_cashflow_repaid),
        "chart_loan_status_labels": json.dumps(chart_loan_status_labels),
        "chart_loan_status_values": json.dumps(chart_loan_status_values),
    }

    return render(request, "dashboard.html", context)
