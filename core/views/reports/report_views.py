# core/views/report_views.py

from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from weasyprint import HTML
from django.template.loader import render_to_string

from core.models import (
    Member,
    CompanyAccount,
    Income,
    Expense,
    Loan,
    LoanDisbursement,
    LoanRepayment,
    Transaction,
)

#===================================================================================================
#===================================================================================================

@login_required
@require_http_methods(["GET"])
def report_filters(request):
    """
    Página onde o utilizador escolhe o tipo de relatório, intervalos de datas e filtros.
    """
    members = Member.objects.filter(is_active=True).order_by("first_name", "last_name")
    users = User.objects.filter(is_active=True, is_superuser=False).order_by("username")
    company_accounts = CompanyAccount.objects.filter(is_active=True).order_by("name")

    context = {
        "segment": "reports",
        "members": members,
        "users": users,
        "company_accounts": company_accounts,
    }
    return render(request, "reports/report_filters.html", context)

#===================================================================================================
#===================================================================================================

@login_required
@require_http_methods(["POST"])
def generate_report_pdf(request):
    """
    Gera o PDF com base no tipo de relatório e filtros escolhidos.
    """
    report_type = request.POST.get("report_type")
    if not report_type:
        return HttpResponseBadRequest(_("Tipo de relatório é obrigatório."))

    # Intervalo de datas (compatível com Python < 3.7 — sem fromisoformat)
    start_date_str = (request.POST.get("start_date") or "").strip()
    end_date_str = (request.POST.get("end_date") or "").strip()

    today = date.today()

    # Data inicial
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponseBadRequest(_("Data inicial inválida."))
    else:
        # primeiro dia do mês actual
        start_date = today.replace(day=1)

    # Data final
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponseBadRequest(_("Data final inválida."))
    else:
        end_date = today

    # Filtros opcionais
    member_id = request.POST.get("member") or None
    user_id = request.POST.get("user") or None
    company_account_id = request.POST.get("company_account") or None

    member_obj = None
    user_obj = None
    account_obj = None

    if member_id:
        member_obj = get_object_or_404(Member, pk=member_id)
    if user_id:
        user_obj = get_object_or_404(User, pk=user_id)
    if company_account_id:
        account_obj = get_object_or_404(CompanyAccount, pk=company_account_id)

    # Mapeamento de label
    REPORT_LABELS = {
        "incomes": _("Rendimentos"),
        "expenses": _("Despesas"),
        "balances": _("Saldos por Conta"),
        "loans": _("Empréstimos"),
        "disbursements": _("Desembolsos"),
        "repayments": _("Reembolsos"),
        "transactions": _("Transacções"),
        "profits": _("Lucros (Rendimentos - Despesas)"),
    }
    report_title = REPORT_LABELS.get(report_type, _("Relatório"))

    context = {
        "report_type": report_type,
        "report_title": report_title,
        "start_date": start_date,
        "end_date": end_date,
        "member": member_obj,
        "user_obj": user_obj,
        "account": account_obj,
        "generated_by": request.user,
    }

    # ===================== LÓGICA POR TIPO =====================

    # 1) RENDIMENTOS
    if report_type == "incomes":
        qs = Income.objects.select_related("category", "company_account").filter(
            income_date__range=(start_date, end_date),
            is_active=True,
        )
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_amount = qs.aggregate(total=Sum("amount"))["total"] or 0
        context["rows"] = qs
        context["total_amount"] = total_amount

    # 2) DESPESAS
    elif report_type == "expenses":
        qs = Expense.objects.select_related("category", "company_account").filter(
            expense_date__range=(start_date, end_date),
            is_active=True,
        )
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_amount = qs.aggregate(total=Sum("amount"))["total"] or 0
        context["rows"] = qs
        context["total_amount"] = total_amount

    # 3) SALDOS – snapshot de todas as contas
    elif report_type == "balances":
        accounts = CompanyAccount.objects.filter(is_active=True).order_by("name")
        context["accounts"] = accounts

    # 4) EMPRÉSTIMOS
    elif report_type == "loans":
        qs = (
            Loan.objects
            .select_related("member", "loan_type", "interest_type", "company_account")
            .filter(created_at__date__range=(start_date, end_date))
        )
        if member_obj:
            qs = qs.filter(member=member_obj)
        if user_obj:
            qs = qs.filter(created_by=user_obj)
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_principal = qs.aggregate(total=Sum("principal_amount"))["total"] or 0
        context["rows"] = qs
        context["total_principal"] = total_principal

    # 5) DESEMBOLSOS
    elif report_type == "disbursements":
        qs = (
            LoanDisbursement.objects
            .select_related("loan", "member", "company_account")
            .filter(disburse_date__range=(start_date, end_date))
        )
        if member_obj:
            qs = qs.filter(member=member_obj)
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_amount = qs.aggregate(total=Sum("amount"))["total"] or 0
        context["rows"] = qs
        context["total_amount"] = total_amount

    # 6) REEMBOLSOS
    elif report_type == "repayments":
        qs = (
            LoanRepayment.objects
            .select_related("loan", "member", "company_account")
            .filter(payment_date__range=(start_date, end_date))
        )
        if member_obj:
            qs = qs.filter(member=member_obj)
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_amount = qs.aggregate(total=Sum("amount"))["total"] or 0
        total_interest = qs.aggregate(total=Sum("interest_amount"))["total"] or 0
        total_principal = qs.aggregate(total=Sum("principal_amount"))["total"] or 0

        context["rows"] = qs
        context["total_amount"] = total_amount
        context["total_interest"] = total_interest
        context["total_principal"] = total_principal

    # 7) TRANSACÇÕES
    elif report_type == "transactions":
        qs = (
            Transaction.objects
            .select_related("company_account")
            .filter(tx_date__range=(start_date, end_date))
        )
        if account_obj:
            qs = qs.filter(company_account=account_obj)

        total_in = qs.filter(tx_type=Transaction.TX_TYPE_IN).aggregate(total=Sum("amount"))["total"] or 0
        total_out = qs.filter(tx_type=Transaction.TX_TYPE_OUT).aggregate(total=Sum("amount"))["total"] or 0

        context["rows"] = qs.order_by("tx_date", "id")
        context["total_in"] = total_in
        context["total_out"] = total_out
        context["net"] = (total_in or 0) - (total_out or 0)

    # 8) LUCROS = Rendimentos - Despesas
    elif report_type == "profits":
        incomes_qs = Income.objects.filter(
            income_date__range=(start_date, end_date),
            is_active=True,
        )
        expenses_qs = Expense.objects.filter(
            expense_date__range=(start_date, end_date),
            is_active=True,
        )
        if account_obj:
            incomes_qs = incomes_qs.filter(company_account=account_obj)
            expenses_qs = expenses_qs.filter(company_account=account_obj)

        total_incomes = incomes_qs.aggregate(total=Sum("amount"))["total"] or 0
        total_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or 0
        profit = total_incomes - total_expenses

        context["total_incomes"] = total_incomes
        context["total_expenses"] = total_expenses
        context["profit"] = profit

    else:
        return HttpResponseBadRequest(_("Tipo de relatório desconhecido."))

    # ===================== GERAR PDF COM WEASYPRINT =====================
    html_string = render_to_string("reports/report_pdf.html", context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_bytes = html.write_pdf()

    filename = f"{report_type}_{start_date}_{end_date}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    # abre em nova aba (inline). Se quiser forçar download, usa attachment.
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response

#===================================================================================================
#===================================================================================================
