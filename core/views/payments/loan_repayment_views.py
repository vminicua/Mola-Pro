from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from datetime import datetime

from core.loan_installment_schedule import (
    allocate_amount_to_installments,
    build_loan_installment_schedule,
)
from core.loan_repayment_logic import quantize_money
from core.models import (
    Loan,
    LoanRepayment,
    CompanyAccount,
    Transaction,
)

#=================================================================================================
#=================================================================================================


def _build_repayment_validation_message(code, **context):
    if code == "no_interest_due":
        return _(
            "A prestação actual já não tem juros em falta. Não é possível liquidar apenas juros."
        )

    if code == "interest_only_exact_amount":
        return _(
            "Para liquidar apenas os juros da prestação actual o valor deve ser exactamente "
            "{interest_remaining}. Introduziu {amount}."
        ).format(
            interest_remaining=context["expected"],
            amount=context["actual"],
        )

    if code == "full_exact_amount":
        return _(
            "Para liquidar totalmente este empréstimo deve pagar exactamente "
            "{total_due_now}. Introduziu {amount}."
        ).format(
            total_due_now=context["expected"],
            amount=context["actual"],
        )

    if code == "partial_must_be_less_than_total_due":
        return _(
            "Para pagamento parcial o valor deve ser inferior ao saldo total em aberto "
            "({total_due_now}). Se pretende liquidar tudo, use 'Liquidar toda a conta'. "
            "Introduziu {amount}."
        ).format(
            total_due_now=context["total_due_now"],
            amount=context["actual"],
        )

    if code == "no_balance_due":
        return _(
            "Este empréstimo já não tem saldo em aberto."
        )

    return _("Falha ao validar o pagamento deste empréstimo.")


#=================================================================================================
#=================================================================================================

@login_required
def loan_repayment_list(request):
    """
    Lista as prestações dos empréstimos em acompanhamento:
    - prestações em aberto e já liquidadas
    - saldo total remanescente por empréstimo
    - prestação actual desbloqueada para pagamento
    """

    loans_qs = (
        Loan.objects
        .select_related("member", "loan_type", "interest_type", "approved_by")
        .prefetch_related("repayments", "repayments__company_account")
        .filter(status__in=["disbursed", "closed"])
        .order_by("-id")
    )

    loans = list(loans_qs)
    total_loans = len(loans)
    total_principal_all = Decimal("0")
    total_outstanding_all = Decimal("0")

    today = timezone.localdate()

    for loan in loans:
        repayments = sorted(
            list(loan.repayments.all()),
            key=lambda item: (item.payment_date, item.id),
        )
        _, schedule_rows, schedule_summary = build_loan_installment_schedule(loan, repayments)
        total_contract_amount = quantize_money(
            sum((row["expected_payment"] for row in schedule_rows), Decimal("0.00"))
        )
        total_paid_amount = quantize_money(
            sum((row["paid_total"] for row in schedule_rows), Decimal("0.00"))
        )
        active_installment = schedule_summary["active_installment"]

        total_principal_all += loan.principal_amount
        loan.total_contract_amount = total_contract_amount
        loan.total_paid_amount = total_paid_amount
        loan.remaining_total_to_repay = schedule_summary["remaining_total"]
        loan.remaining_principal_to_repay = schedule_summary["remaining_principal"]
        loan.active_installment = active_installment
        loan.completed_installments = schedule_summary["completed_installments"]
        loan.total_installments = schedule_summary["total_installments"]
        loan.is_repaid = loan.status == "closed" or loan.remaining_total_to_repay <= 0
        loan.repayment_filter_status = "repaid" if loan.is_repaid else "outstanding"
        loan.installment_rows = schedule_rows
        loan.next_due_date = active_installment["due_date"] if active_installment else None
        loan.next_installment_amount = active_installment["remaining_total"] if active_installment else Decimal("0.00")
        loan.next_installment_number = active_installment["installment_number"] if active_installment else 0
        loan.next_installment_label = active_installment["installment_label"] if active_installment else ""
        loan.next_installment_expected = active_installment["expected_payment"] if active_installment else Decimal("0.00")
        loan.next_installment_paid = active_installment["paid_total"] if active_installment else Decimal("0.00")
        loan.next_installment_interest_remaining = active_installment["remaining_interest"] if active_installment else Decimal("0.00")
        loan.is_next_installment_overdue = bool(
            active_installment and active_installment.get("due_date") and active_installment["due_date"] < today
        )

        total_outstanding_all += loan.remaining_total_to_repay

        last_rep = repayments[-1] if repayments else None
        loan.last_repayment = last_rep
        loan.last_repayment_amount = last_rep.amount if last_rep else None

        for row in schedule_rows:
            row["loan"] = loan
            row["filter_status"] = loan.repayment_filter_status
            row["loan_remaining_total"] = loan.remaining_total_to_repay
            row["last_repayment"] = last_rep

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
    - interest_only: paga apenas os juros ainda em falta da prestação actual.
    - full: liquida todo o saldo remanescente do contrato.
    - partial: aplica qualquer valor positivo a partir da prestação actual,
               afectando prestações seguintes quando houver excesso.
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

    repayments = list(loan.repayments.all())
    _, schedule_rows, schedule_summary = build_loan_installment_schedule(loan, repayments)
    remaining_total = schedule_summary["remaining_total"]
    remaining_principal = schedule_summary["remaining_principal"]
    active_installment = schedule_summary["active_installment"]

    if remaining_total <= 0:
        return JsonResponse(
            {"success": False, "message": _("Este empréstimo já não tem saldo em aberto.")},
            status=400,
        )

    # ===== 3) VALIDAR E DISTRIBUIR O PAGAMENTO =====
    repayment_type_label_map = {
        "interest_only": _("Pagamento apenas de juros da prestação actual"),
        "full": _("Liquidação total do contrato"),
        "partial": _("Pagamento parcial por prestações"),
    }
    repayment_type_label = repayment_type_label_map[repayment_type]
    allocation = None

    if repayment_type == "interest_only":
        expected_interest = active_installment["remaining_interest"] if active_installment else Decimal("0.00")
        if expected_interest <= 0:
            return JsonResponse(
                {"success": False, "message": _build_repayment_validation_message("no_interest_due")},
                status=400,
            )

        if amount != expected_interest:
            return JsonResponse(
                {
                    "success": False,
                    "message": _build_repayment_validation_message(
                        "interest_only_exact_amount",
                        expected=expected_interest,
                        actual=amount,
                    ),
                },
                status=400,
            )

        allocation = allocate_amount_to_installments(schedule_rows, amount)

    elif repayment_type == "full":
        if amount != remaining_total:
            return JsonResponse(
                {
                    "success": False,
                    "message": _build_repayment_validation_message(
                        "full_exact_amount",
                        expected=remaining_total,
                        actual=amount,
                    ),
                },
                status=400,
            )

        allocation = allocate_amount_to_installments(schedule_rows, amount)

    else:
        repayment_type = "partial"
        repayment_type_label = repayment_type_label_map[repayment_type]

        if amount >= remaining_total:
            return JsonResponse(
                {
                    "success": False,
                        "message": _build_repayment_validation_message(
                            "partial_must_be_less_than_total_due",
                            total_due_now=remaining_total,
                            actual=amount,
                        ),
                    },
                status=400,
            )

        allocation = allocate_amount_to_installments(schedule_rows, amount)

    if allocation["unallocated_amount"] > Decimal("0.00"):
        return JsonResponse(
            {"success": False, "message": _("Falha ao distribuir o pagamento pelas prestações em aberto.")},
            status=400,
        )

    interest_amount = allocation["interest_amount"]
    principal_amount = allocation["principal_amount"]
    principal_balance_after = quantize_money(max(remaining_principal - principal_amount, Decimal("0.00")))
    remaining_total_after = quantize_money(max(remaining_total - allocation["total_applied"], Decimal("0.00")))

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

    if remaining_total_after <= 0:
        loan.status = "closed"
        loan.save(update_fields=["status"])

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
