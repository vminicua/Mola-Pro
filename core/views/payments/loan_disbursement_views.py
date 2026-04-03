from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.db.models import F, ExpressionWrapper, DecimalField, Q
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.models import (
    Loan,
    LoanDisbursement,
    CompanyAccount,
    Transaction,
)

#============================================================================================================
#============================================================================================================
@login_required
def loan_disbursement_list(request):
    """
    Lista empréstimos aprovados por desembolsar e empréstimos já desembolsados.
    - Calcula total_to_repay = payment_per_period * term_periods
    - Calcula total_interest = total_to_repay - principal_amount
    - Anexa info da conta do cliente (nome + número) ao objecto loan
    """
    loans_qs = (
        Loan.objects
        .select_related("member", "loan_type", "approved_by")
        .prefetch_related(
            "disbursements",
            "disbursements__company_account",
            "member__client_accounts__account_type",
        )
        .filter(Q(status="approved") | Q(disbursements__isnull=False))
        .annotate(
            total_to_repay=ExpressionWrapper(
                F("payment_per_period") * F("term_periods"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
            total_interest=ExpressionWrapper(
                F("payment_per_period") * F("term_periods") - F("principal_amount"),
                output_field=DecimalField(max_digits=15, decimal_places=2),
            ),
        )
        .distinct()
        .order_by("-id")
    )

    # Transformar em lista para podermos anexar atributos calculados em Python
    loans = list(loans_qs)

    for loan in loans:
        disbursement_records = list(loan.disbursements.all())
        loan.has_disbursement = len(disbursement_records) > 0

        # primeira conta activa do cliente (se existir)
        ca = (
            loan.member.client_accounts
            .filter(is_active=True)
            .select_related("account_type")
            .order_by("id")
            .first()
        )

        if ca:
            loan.client_account_name_to_credit = (
                f"{ca.account_type.get_category_display()} · {ca.account_type.name}"
            )
            loan.client_account_identifier_to_credit = ca.account_identifier
        else:
            loan.client_account_name_to_credit = ""
            loan.client_account_identifier_to_credit = ""

    company_accounts = CompanyAccount.objects.filter(is_active=True).order_by("name")

    context = {
        "loans": loans,
        "company_accounts": company_accounts,
        "segment": "loan_disbursements",
    }
    return render(request, "payments/loan_disbursement_list.html", context)

#============================================================================================================
#============================================================================================================
@login_required
@require_POST
@db_transaction.atomic
def register_disbursement(request, loan_id):
    """
    Regista o desembolso de um empréstimo:
    - verifica saldo disponível na conta da empresa
    - exige comprovativo do desembolso
    - cria LoanDisbursement
    - cria Transaction (saída)
    - actualiza saldo da conta da empresa
    - muda Loan.status para 'disbursed'
    - regista opcionalmente o nome/número da conta do cliente utilizada
    """
    loan = get_object_or_404(
        Loan.objects.select_related("member"),
        pk=loan_id
    )

    if loan.status != "approved":
        return JsonResponse(
            {"success": False, "message": _("Apenas empréstimos aprovados podem ser desembolsados.")},
            status=400,
        )

    if loan.disbursements.exists():
        return JsonResponse(
            {"success": False, "message": _("Este empréstimo já foi desembolsado.")},
            status=400,
        )

    company_account_id = request.POST.get("company_account", "").strip()
    disburse_date_str = request.POST.get("disburse_date", "").strip()
    amount_raw = request.POST.get("amount", "").strip()
    method = request.POST.get("method", "cash").strip()
    notes = request.POST.get("notes", "").strip()
    attachment = request.FILES.get("attachment")

    # NOVOS CAMPOS: conta do cliente a creditar (opcionais)
    client_account_name = request.POST.get("client_account_name", "").strip()
    client_account_number = request.POST.get("client_account_number", "").strip()

    # Conta da empresa
    if not company_account_id:
        return JsonResponse(
            {"success": False, "message": _("Selecione a conta da empresa para o desembolso.")},
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
    if not disburse_date_str:
        return JsonResponse(
            {"success": False, "message": _("Informe a data de desembolso.")},
            status=400,
        )
    try:
        disburse_date = datetime.strptime(disburse_date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {"success": False, "message": _("Data de desembolso inválida.")},
            status=400,
        )

    # Valor
    if not amount_raw:
        return JsonResponse(
            {"success": False, "message": _("Informe o valor de desembolso.")},
            status=400,
        )
    try:
        amount = Decimal(str(amount_raw))
        if amount <= 0:
            raise ValueError
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Valor de desembolso inválido.")},
            status=400,
        )

    if not attachment:
        return JsonResponse(
            {"success": False, "message": _("Anexe o comprovativo do desembolso.")},
            status=400,
        )

    # Verificar saldo disponível
    current_balance = account.balance or Decimal("0")
    if amount > current_balance:
        return JsonResponse(
            {
                "success": False,
                "message": _(
                    "Saldo insuficiente na conta seleccionada para efectuar este desembolso. "
                    "Por favor registe primeiro uma entrada de saldo (depósito/crédito) "
                    "na conta da empresa antes de desembolsar."
                ),
            },
            status=400,
        )

    # Criar LoanDisbursement
    disb = LoanDisbursement.objects.create(
        loan=loan,
        member=loan.member,
        company_account=account,
        disburse_date=disburse_date,
        amount=amount,
        method=method,
        attachment=attachment,
        notes=notes or None,
    )

    # Actualizar saldo da conta
    old_balance = current_balance
    account.balance = old_balance - amount
    account.save(update_fields=["balance"])
    new_balance = account.balance

    # Descrição da transacção, incluindo info da conta do cliente (se fornecida)
    desc = _("Desembolso de empréstimo (Loan #{loan_id}) para {member_name}").format(
        loan_id=loan.id,
        member_name=f"{loan.member.first_name} {loan.member.last_name}",
    )

    if client_account_name or client_account_number:
        desc += _(" | Conta cliente: ")
        if client_account_name:
            desc += client_account_name
        if client_account_number:
            desc += f" ({client_account_number})"

    # Transacção de saída
    Transaction.objects.create(
        company_account=account,
        tx_type=Transaction.TX_TYPE_OUT,
        source_type="loan_disbursement",
        source_id=disb.id,
        tx_date=disburse_date,
        description=desc,
        amount=amount,
        balance_before=old_balance,
        balance_after=new_balance,
        is_active=True,
        created_at=timezone.now(),
    )

    loan.status = "disbursed"
    loan.save(update_fields=["status"])

    return JsonResponse(
        {"success": True, "message": _("Desembolso registado com sucesso.")}
    )
#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================
