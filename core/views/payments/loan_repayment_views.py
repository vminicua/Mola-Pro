from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from datetime import datetime

from core.loan_math import calculate_flat_loan_metrics
from core.loan_repayment_logic import (
    RepaymentAllocationError,
    add_period,
    allocate_repayment,
    quantize_money,
)
from core.models import (
    Loan,
    LoanRepayment,
    CompanyAccount,
    Transaction,
)

#=================================================================================================
#=================================================================================================


def _build_loan_repayment_snapshot(loan, repayments):
    agg_tot = repayments.aggregate(total_principal=Sum("principal_amount"))
    principal_paid_total = agg_tot["total_principal"] or Decimal("0")
    outstanding_principal = loan.principal_amount - principal_paid_total
    if outstanding_principal < 0:
        outstanding_principal = Decimal("0")

    cycle_start = loan.release_date or loan.created_at.date()
    cycle_due = loan.first_payment_date

    agg_before = repayments.filter(payment_date__lt=cycle_start).aggregate(
        total_before=Sum("principal_amount")
    )
    principal_paid_before_cycle = agg_before["total_before"] or Decimal("0")
    cycle_base_principal = loan.principal_amount - principal_paid_before_cycle
    if cycle_base_principal < 0:
        cycle_base_principal = Decimal("0")

    rate = loan.interest_type.rate if loan.interest_type and loan.interest_type.rate else Decimal("0")
    rate_decimal = (rate / Decimal("100")).quantize(Decimal("0.0001"))
    cycle_interest_total = (cycle_base_principal * rate_decimal).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    q_cycle = Q(payment_date__gte=cycle_start)
    if cycle_due:
        q_cycle &= Q(payment_date__lte=cycle_due)

    agg_int = repayments.filter(q_cycle).aggregate(total_int=Sum("interest_amount"))
    interest_paid_cycle = agg_int["total_int"] or Decimal("0")
    interest_remaining = cycle_interest_total - interest_paid_cycle
    if interest_remaining < 0:
        interest_remaining = Decimal("0")

    metrics = calculate_flat_loan_metrics(
        loan.principal_amount,
        getattr(loan.interest_type, "rate", Decimal("0")) or Decimal("0"),
        loan.term_periods,
    )
    scheduled_payment_per_period = quantize_money(
        loan.payment_per_period or metrics["suggested_payment_per_period"]
    )
    outstanding_with_interest = quantize_money(outstanding_principal + interest_remaining)
    payment_due_this_cycle = (
        min(scheduled_payment_per_period, outstanding_with_interest)
        if scheduled_payment_per_period > 0
        else outstanding_with_interest
    )

    return {
        "outstanding_principal": quantize_money(outstanding_principal),
        "cycle_start": cycle_start,
        "cycle_due": cycle_due,
        "cycle_base_principal": quantize_money(cycle_base_principal),
        "cycle_interest_total": quantize_money(cycle_interest_total),
        "interest_paid_cycle": quantize_money(interest_paid_cycle),
        "interest_remaining": quantize_money(interest_remaining),
        "outstanding_with_interest": outstanding_with_interest,
        "scheduled_payment_per_period": scheduled_payment_per_period,
        "payment_due_this_cycle": quantize_money(payment_due_this_cycle),
    }


def _build_repayment_validation_message(exc: RepaymentAllocationError):
    if exc.code == "no_interest_due":
        return _(
            "Não há juros em falta neste ciclo. Não é possível liquidar apenas juros."
        )

    if exc.code == "interest_only_exact_amount":
        return _(
            "Para liquidar apenas os juros deste ciclo o valor deve ser exactamente "
            "{interest_remaining}. Introduziu {amount}."
        ).format(
            interest_remaining=exc.context["expected"],
            amount=exc.context["actual"],
        )

    if exc.code == "full_exact_amount":
        return _(
            "Para liquidar totalmente este empréstimo deve pagar exactamente "
            "{total_due_now}. Introduziu {amount}."
        ).format(
            total_due_now=exc.context["expected"],
            amount=exc.context["actual"],
        )

    if exc.code == "partial_must_reduce_principal":
        return _(
            "Para pagamento parcial neste ciclo o valor deve ser superior aos juros em falta "
            "({interest_remaining}) para também amortizar principal. Se pretende pagar só juros, "
            "use 'Liquidar apenas juros'. Introduziu {amount}."
        ).format(
            interest_remaining=exc.context["interest_remaining"],
            amount=exc.context["actual"],
        )

    if exc.code == "partial_must_be_less_than_total_due":
        return _(
            "Para pagamento parcial o valor deve ser inferior ao saldo total em dívida "
            "({total_due_now}). Se pretende encerrar o empréstimo, use 'Liquidar toda a conta'. "
            "Introduziu {amount}."
        ).format(
            total_due_now=exc.context["total_due_now"],
            amount=exc.context["actual"],
        )

    return _("Falha ao validar o pagamento deste empréstimo.")


#=================================================================================================
#=================================================================================================

@login_required
def loan_repayment_list(request):
    """
    Lista empréstimos com status 'disbursed' e mostra:
    - principal em dívida (outstanding_principal)
    - juros do período (total e em falta) com base no ciclo actual
    - saldo em dívida = principal em dívida + juros em falta
    - próximo vencimento (loan.first_payment_date)
    """

    loans_qs = (
        Loan.objects
        .select_related("member", "loan_type", "interest_type", "approved_by")
        .prefetch_related("repayments", "repayments__company_account")
        .filter(status="disbursed")
        .order_by("-id")
    )

    loans = list(loans_qs)

    total_loans = len(loans)
    total_principal_all = Decimal("0")
    total_outstanding_all = Decimal("0")

    today = timezone.localdate()

    for loan in loans:
        repayments = loan.repayments.all()
        snapshot = _build_loan_repayment_snapshot(loan, repayments)

        loan.outstanding_principal = snapshot["outstanding_principal"]
        total_principal_all += loan.principal_amount
        loan.current_cycle_start = snapshot["cycle_start"]
        loan.current_cycle_due = snapshot["cycle_due"]
        loan.period_interest_total = snapshot["cycle_interest_total"]
        loan.period_interest_remaining = snapshot["interest_remaining"]
        loan.outstanding_with_interest = snapshot["outstanding_with_interest"]
        loan.scheduled_payment_per_period = snapshot["scheduled_payment_per_period"]
        loan.payment_due_this_cycle = snapshot["payment_due_this_cycle"]

        total_outstanding_all += loan.outstanding_with_interest

        last_rep = repayments.order_by("-payment_date", "-id").first()
        loan.last_repayment = last_rep

    context = {
        "loans": loans,
        "segment": "loan_repayments",
        "kpi_total_loans": total_loans,
        "kpi_total_principal": total_principal_all,
        "kpi_total_outstanding": total_outstanding_all,
        "kpi_avg_outstanding": (total_outstanding_all / total_loans) if total_loans else Decimal("0"),
        "company_accounts": CompanyAccount.objects.filter(is_active=True).order_by("name"),
        "today": today,
    }
    return render(request, "payments/loan_repayment_list.html", context)

#=================================================================================================
#=================================================================================================
@login_required
@require_POST
@db_transaction.atomic
def register_repayment(request, loan_id):
    """
    Regista um reembolso de empréstimo com 3 opções:
    - interest_only: paga apenas juros em falta deste ciclo (principal mantém-se);
                     renova a validade no próximo período do empréstimo.
    - full: paga juros em falta + 100% do principal em dívida (fecha o empréstimo).
    - partial: paga juros em falta + parte do principal (reduz saldo do principal).
    Em todos os casos:
    - cria LoanRepayment
    - actualiza saldo da conta da empresa (entrada)
    - cria Transaction (IN, source_type='loan_repayment')
    """

    loan = get_object_or_404(
        Loan.objects.select_related("member", "interest_type"),
        pk=loan_id,
        status="disbursed",
    )

    repayment_type = request.POST.get("repayment_type", "partial").strip()  # interest_only / full / partial
    if repayment_type not in {"interest_only", "full", "partial"}:
        repayment_type = "partial"

    company_account_id = request.POST.get("company_account", "").strip()
    payment_date_str = request.POST.get("payment_date", "").strip()
    amount_raw = request.POST.get("amount", "").strip()
    method = request.POST.get("method", "cash").strip()
    notes = request.POST.get("notes", "").strip()
    attachment = request.FILES.get("attachment")

    # Conta da empresa
    if not company_account_id:
        return JsonResponse(
            {"success": False, "message": _("Selecione a conta da empresa que recebe o pagamento.")},
            status=400,
        )
    try:
        account = CompanyAccount.objects.get(pk=company_account_id, is_active=True)
    except CompanyAccount.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Conta da empresa inválida.")},
            status=400,
        )

    # Data
    if not payment_date_str:
        return JsonResponse(
            {"success": False, "message": _("Informe a data de pagamento.")},
            status=400,
        )
    try:
        payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"success": False, "message": _("Data de pagamento inválida.")},
            status=400,
        )

    # Valor
    if not amount_raw:
        return JsonResponse(
            {"success": False, "message": _("Informe o valor do pagamento.")},
            status=400,
        )
    try:
        amount = quantize_money(amount_raw)
        if amount <= 0:
            raise ValueError
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Valor do pagamento inválido.")},
            status=400,
        )

    repayments = loan.repayments.all()
    snapshot = _build_loan_repayment_snapshot(loan, repayments)
    outstanding_principal = snapshot["outstanding_principal"]
    if outstanding_principal <= 0:
        return JsonResponse(
            {"success": False, "message": _("Este empréstimo não tem saldo de principal em dívida.")},
            status=400,
        )

    interest_remaining = snapshot["interest_remaining"]

    # ===== 3) VALIDAR E DISTRIBUIR O PAGAMENTO =====
    repayment_type_label_map = {
        "interest_only": _("Pagamento apenas de juros"),
        "full": _("Liquidação total (juros + principal)"),
        "partial": _("Pagamento parcial (juros + principal)"),
    }
    repayment_type_label = repayment_type_label_map[repayment_type]

    try:
        allocation = allocate_repayment(
            amount=amount,
            interest_remaining=interest_remaining,
            outstanding_principal=outstanding_principal,
            repayment_type=repayment_type,
        )
    except RepaymentAllocationError as exc:
        return JsonResponse(
            {"success": False, "message": _build_repayment_validation_message(exc)},
            status=400,
        )

    interest_amount = allocation.interest_amount
    principal_amount = allocation.principal_amount
    principal_balance_after = allocation.principal_balance_after

    # ===== 4) CRIAR LOANREPAYMENT =====
    repayment = LoanRepayment.objects.create(
        loan=loan,
        member=loan.member,
        company_account=account,
        payment_date=payment_date,
        amount=amount,
        interest_amount=interest_amount,
        principal_amount=principal_amount,
        principal_balance_after=principal_balance_after,
        method=method,
        attachment=attachment,
        notes=notes or None,
    )

    # ===== 5) ACTUALIZAR SALDO DA CONTA DA EMPRESA =====
    old_balance = account.balance or Decimal("0")
    account.balance = old_balance + amount
    account.save(update_fields=["balance"])
    new_balance = account.balance

    # ===== 6) REGISTAR TRANSAÇÃO =====
    descricao = _(
        "{repayment_type_label} - Reembolso de empréstimo (Loan #{loan_id}) "
        "de {member_name} - Juros: {interest_amount} · Principal: {principal_amount}"
    ).format(
        repayment_type_label=repayment_type_label,
        loan_id=loan.id,
        member_name=f"{loan.member.first_name} {loan.member.last_name}",
        interest_amount=interest_amount,
        principal_amount=principal_amount,
    )

    Transaction.objects.create(
        company_account=account,
        tx_type=Transaction.TX_TYPE_IN,
        source_type="loan_repayment",
        source_id=repayment.id,
        tx_date=payment_date,
        description=descricao,
        amount=amount,
        balance_before=old_balance,
        balance_after=new_balance,
        is_active=True,
        created_at=timezone.now(),
    )

    # ===== 7) ACTUALIZAR ESTADO / VALIDADE DO EMPRÉSTIMO =====

    # Se principal acabou, fecha empréstimo
    if principal_balance_after <= 0:
        loan.status = "closed"
        loan.save(update_fields=["status"])

    # Se foi "apenas juros": renova validade no próximo período configurado
    elif repayment_type == "interest_only":
        loan.release_date = payment_date
        loan.first_payment_date = add_period(payment_date, loan.period_type, 1)
        loan.save(update_fields=["release_date", "first_payment_date"])

    # Pagamento parcial: apenas reduz principal; ciclo continua igual

    return JsonResponse(
        {
            "success": True,
            "message": _(
                "{repayment_type_label} registado com sucesso. "
                "Juros pagos: {interest_amount}, principal amortizado: {principal_amount}, "
                "saldo de principal em dívida após pagamento: {principal_balance_after}."
            ).format(
                repayment_type_label=repayment_type_label,
                interest_amount=interest_amount,
                principal_amount=principal_amount,
                principal_balance_after=principal_balance_after,
            ),
        }
    )

#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================


#=================================================================================================
#=================================================================================================
