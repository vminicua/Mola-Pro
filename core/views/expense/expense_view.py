from django.utils import timezone
from decimal import Decimal
from django.shortcuts import render, redirect
from core.models import (
    Member,
    AccountType,
    ClientAccount,
    CompanyAccount,
    ExpenseCategory,
    Expense,
    Transaction,
)
from django.views.decorators.http import require_POST
import os
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _

#============================================================================================================
#============================================================================================================

def expense_category_list(request):
    categories = ExpenseCategory.objects.order_by("name")
    return render(
        request,
        "expenses/expense_category_list.html",
        {"categories": categories,
         "segment": "expense_categories",},
    )
#============================================================================================================
#============================================================================================================

@require_POST
def create_expense_category(request):
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse(
            {"success": False, "message": _("Nome da categoria é obrigatório.")},
            status=400,
        )

    ExpenseCategory.objects.create(
        name=name,
        description=description or None,
        is_active=True,
    )

    return JsonResponse(
        {"success": True, "message": _("Categoria de despesa criada com sucesso.")}
    )

#============================================================================================================
#============================================================================================================

@require_POST
def update_expense_category(request):
    cat_id = request.POST.get("id", "").strip()
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()

    if not cat_id:
        return JsonResponse(
            {"success": False, "message": _("ID da categoria é obrigatório.")},
            status=400,
        )

    if not name:
        return JsonResponse(
            {"success": False, "message": _("Nome da categoria é obrigatório.")},
            status=400,
        )

    category = get_object_or_404(ExpenseCategory, pk=cat_id)

    category.name = name
    category.description = description or None
    category.save(update_fields=["name", "description"])

    return JsonResponse(
        {"success": True, "message": _("Categoria de despesa actualizada com sucesso.")}
    )


#============================================================================================================
#============================================================================================================

@require_POST
def deactivate_expense_category(request):
    cat_id = request.POST.get("id", "").strip()

    if not cat_id:
        return JsonResponse(
            {"success": False, "message": _("ID da categoria é obrigatório.")},
            status=400,
        )

    category = get_object_or_404(ExpenseCategory, pk=cat_id, is_active=True)

    category.is_active = False
    category.save(update_fields=["is_active"])

    return JsonResponse(
        {"success": True, "message": _("Categoria de despesa desactivada com sucesso.")}
    )
#============================================================================================================
#============================================================================================================


def expense_list(request):
    categories = ExpenseCategory.objects.filter(is_active=True).order_by("name")
    company_accounts = CompanyAccount.objects.filter(is_active=True).order_by("name")

    expenses = (
        Expense.objects.filter(is_active=True)
        .select_related("category", "company_account", "created_by")
        .order_by("-expense_date", "-id")
    )

    return render(
        request,
        "expenses/expense_list.html",
        {
            "categories": categories,
            "company_accounts": company_accounts,
            "expenses": expenses,
            "segment": "expenses",
        },
    )



#============================================================================================================
#============================================================================================================
#============================================================================================================
#============================================================================================================
@require_POST
def create_expense(request):
    category_id = request.POST.get("category", "").strip()
    company_account_id = request.POST.get("company_account", "").strip()
    expense_date = request.POST.get("expense_date", "").strip()
    description = request.POST.get("description", "").strip()
    amount_raw = request.POST.get("amount", "").strip()
    attachment_file = request.FILES.get("attachment")

    if not category_id or not company_account_id or not expense_date or not description or not amount_raw:
        return JsonResponse(
            {
                "success": False,
                "message": _("Categoria, conta da empresa, data, descrição e valor são obrigatórios."),
            },
            status=400,
        )

    try:
        category = ExpenseCategory.objects.get(pk=category_id, is_active=True)
    except ExpenseCategory.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Categoria inválida.")},
            status=400,
        )

    try:
        company_account = CompanyAccount.objects.get(pk=company_account_id, is_active=True)
    except CompanyAccount.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Conta da empresa inválida.")},
            status=400,
        )

    try:
        amount = Decimal(str(amount_raw))
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Valor inválido.")},
            status=400,
        )

    # Validar formato da data
    try:
        timezone.datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        return JsonResponse(
            {"success": False, "message": _("Data inválida.")},
            status=400,
        )

    # Saldo antes
    old_balance = company_account.balance or Decimal("0")
    new_balance = old_balance - amount

    # Criar despesa
    expense = Expense(
        category=category,
        company_account=company_account,
        expense_date=expense_date,
        description=description,
        amount=amount,
        is_active=True,
        created_at=timezone.now(),
        created_by=request.user,   # <<< NOVO
    )
    if attachment_file:
        expense.attachment = attachment_file
    expense.save()

    # Actualizar saldo da conta
    company_account.balance = new_balance
    company_account.save(update_fields=["balance"])

    # Criar transacção (saída)
    Transaction.objects.create(
        company_account=company_account,
        tx_type=Transaction.TX_TYPE_OUT,
        source_type="expense",
        source_id=expense.id,
        tx_date=expense_date,
        description=_("Despesa: {description}").format(description=description),
        amount=amount,
        balance_before=old_balance,
        balance_after=new_balance,
        is_active=True,
        created_at=timezone.now(),
    )

    return JsonResponse(
        {"success": True, "message": _("Despesa registada, saldo deduzido e transacção criada com sucesso.")}
    )





#============================================================================================================
#============================================================================================================


def download_expense_attachment(request, expense_id):
    try:
        expense = Expense.objects.get(pk=expense_id, is_active=True)
    except Expense.DoesNotExist:
        raise Http404(_("Despesa não encontrada."))

    if not expense.attachment:
        raise Http404(_("Nenhum anexo disponível para esta despesa."))

    # Usa o storage do próprio FileField
    file_handle = expense.attachment.open("rb")
    filename = os.path.basename(expense.attachment.name)

    response = FileResponse(file_handle, as_attachment=True, filename=filename)
    return response


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================
