from core.models import Member, AccountType, ClientAccount, CompanyAccount, Transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import render
from decimal import Decimal
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _



#============================================================================================================
#============================================================================================================
def account_type_list(request):
    account_types = AccountType.objects.filter(is_active=True).order_by("id")
    return render(
        request,
        "accounts/account_type_list.html",
        {"account_types": account_types,
         "segment": "account_types",},
    )

#============================================================================================================
#============================================================================================================

@require_POST
def create_account_type(request):
    category = request.POST.get("category", "").strip()
    name = request.POST.get("name", "").strip()

    if not category or not name:
        return JsonResponse(
            {"success": False, "message": _("Categoria e nome são obrigatórios.")},
            status=400,
        )

    if category not in ["cash", "mobile", "bank"]:
        return JsonResponse(
            {"success": False, "message": _("Categoria inválida.")},
            status=400,
        )

    account_type = AccountType.objects.create(
        category=category,
        name=name,
        is_active=True,
    )

    return JsonResponse(
        {
            "success": True,
            "message": _("Tipo de conta criado com sucesso."),
            "id": account_type.id,
        }
    )
#============================================================================================================
#============================================================================================================
@require_POST
def update_account_type(request):
    at_id = request.POST.get("id", "").strip()
    category = request.POST.get("category", "").strip()
    name = request.POST.get("name", "").strip()

    if not at_id:
        return JsonResponse(
            {"success": False, "message": _("ID do tipo de conta é obrigatório.")},
            status=400,
        )

    if not category or not name:
        return JsonResponse(
            {"success": False, "message": _("Categoria e nome são obrigatórios.")},
            status=400,
        )

    if category not in ["cash", "mobile", "bank"]:
        return JsonResponse(
            {"success": False, "message": _("Categoria inválida.")},
            status=400,
        )

    account_type = get_object_or_404(AccountType, pk=at_id)

    account_type.category = category
    account_type.name = name
    account_type.save(update_fields=["category", "name"])

    return JsonResponse(
        {"success": True, "message": _("Tipo de conta actualizado com sucesso.")}
    )


#============================================================================================================
#============================= ACTIVAR / DESACTIVAR TIPO DE CONTA ===========================================
#============================================================================================================
@require_POST
def toggle_account_type_status(request):
    at_id = request.POST.get("id", "").strip()

    if not at_id:
        return JsonResponse(
            {"success": False, "message": _("ID do tipo de conta é obrigatório.")},
            status=400,
        )

    account_type = get_object_or_404(AccountType, pk=at_id)

    account_type.is_active = not account_type.is_active
    account_type.save(update_fields=["is_active"])

    status_label = _("activado") if account_type.is_active else _("desactivado")

    return JsonResponse(
        {
            "success": True,
            "message": _("Tipo de conta {status_label} com sucesso.").format(status_label=status_label),
            "is_active": account_type.is_active,
        }
    )
#============================================================================================================
#============================================================================================================
def client_account_list(request):
    members = Member.objects.filter(is_active=True).order_by("first_name", "last_name")
    account_types = AccountType.objects.filter(is_active=True).order_by("id")
    accounts = (
        ClientAccount.objects.filter(is_active=True)
        .select_related("member", "account_type")
        .order_by("member__first_name", "member__last_name")
    )

    return render(
        request,
        "accounts/client_account_list.html",
        {
            "accounts": accounts,
            "segment": "client_accounts",
            "members": members,
            "account_types": account_types,
        },
    )

#============================================================================================================
#============================================================================================================

@require_POST
def create_client_account(request):
    member_id = request.POST.get("member", "").strip()
    account_type_id = request.POST.get("account_type", "").strip()
    account_identifier = request.POST.get("account_identifier", "").strip()
    balance_raw = request.POST.get("balance", "").strip()

    if not member_id or not account_type_id or not account_identifier:
        return JsonResponse(
            {
                "success": False,
                "message": _("Membro, tipo de conta e identificador são obrigatórios."),
            },
            status=400,
        )

    try:
        member = Member.objects.get(pk=member_id, is_active=True)
    except Member.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Membro inválido.")},
            status=400,
        )

    try:
        account_type = AccountType.objects.get(pk=account_type_id, is_active=True)
    except AccountType.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Tipo de conta inválido.")},
            status=400,
        )

    try:
        balance = float(balance_raw) if balance_raw else 0.0
    except ValueError:
        return JsonResponse(
            {"success": False, "message": _("Saldo inválido.")},
            status=400,
        )

    ClientAccount.objects.create(
        member=member,
        account_type=account_type,
        account_identifier=account_identifier,
        balance=balance,
        is_active=True,
    )

    return JsonResponse(
        {"success": True, "message": _("Conta de cliente criada com sucesso.")}
    )

#============================================================================================================
#============================================================================================================
@require_POST
def update_client_account(request):
    account_id = request.POST.get("id", "").strip()
    member_id = request.POST.get("member", "").strip()
    account_type_id = request.POST.get("account_type", "").strip()
    account_identifier = request.POST.get("account_identifier", "").strip()
    balance_raw = request.POST.get("balance", "").strip()

    if not account_id:
        return JsonResponse(
            {"success": False, "message": _("ID da conta é obrigatório.")},
            status=400,
        )

    if not member_id or not account_type_id or not account_identifier:
        return JsonResponse(
            {
                "success": False,
                "message": _("Membro, tipo de conta e identificador são obrigatórios."),
            },
            status=400,
        )

    account = get_object_or_404(ClientAccount, pk=account_id)

    try:
        member = Member.objects.get(pk=member_id, is_active=True)
    except Member.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Membro inválido.")},
            status=400,
        )

    try:
        account_type = AccountType.objects.get(pk=account_type_id, is_active=True)
    except AccountType.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Tipo de conta inválido.")},
            status=400,
        )

    try:
        balance = Decimal(str(balance_raw)) if balance_raw else Decimal("0")
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Saldo inválido.")},
            status=400,
        )

    account.member = member
    account.account_type = account_type
    account.account_identifier = account_identifier
    account.balance = balance
    account.save(update_fields=["member", "account_type", "account_identifier", "balance"])

    return JsonResponse(
        {"success": True, "message": _("Conta de cliente actualizada com sucesso.")}
    )


#============================================================================================================
#============================= ACTIVAR / DESACTIVAR CONTA DE CLIENTE ========================================
#============================================================================================================
@require_POST
def toggle_client_account_status(request):
    account_id = request.POST.get("id", "").strip()

    if not account_id:
        return JsonResponse(
            {"success": False, "message": _("ID da conta é obrigatório.")},
            status=400,
        )

    account = get_object_or_404(ClientAccount, pk=account_id)

    account.is_active = not account.is_active
    account.save(update_fields=["is_active"])

    status_label = _("activada") if account.is_active else _("desactivada")

    return JsonResponse(
        {
            "success": True,
            "message": _("Conta de cliente {status_label} com sucesso.").format(status_label=status_label),
            "is_active": account.is_active,
        }
    )

#============================================================================================================
#============================================================================================================
def company_account_list(request):
    account_types = AccountType.objects.filter(is_active=True).order_by("id")
    accounts = (
        CompanyAccount.objects.filter(is_active=True)
        .select_related("account_type")
        .order_by("id")
    )

    return render(
        request,
        "accounts/company_account_list.html",
        {
            "accounts": accounts,
            "segment": "company_accounts",
            "account_types": account_types,
        },
    )

#============================================================================================================
#============================================================================================================
@require_POST
def create_company_account(request):
    account_type_id = request.POST.get("account_type", "").strip()
    name = request.POST.get("name", "").strip()
    account_identifier = request.POST.get("account_identifier", "").strip()

    if not account_type_id or not name or not account_identifier:
        return JsonResponse(
            {
                "success": False,
                "message": _("Tipo de conta, nome e identificador são obrigatórios."),
            },
            status=400,
        )

    try:
        account_type = AccountType.objects.get(pk=account_type_id, is_active=True)
    except AccountType.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": _("Tipo de conta inválido.")},
            status=400,
        )

    CompanyAccount.objects.create(
        account_type=account_type,
        name=name,
        account_identifier=account_identifier,
        is_active=True,
    )

    return JsonResponse(
        {"success": True, "message": _("Conta da empresa criada com sucesso.")}
    )

#============================================================================================================
#============================================================================================================
@require_POST
def update_company_account(request, account_id):
    try:
        account = CompanyAccount.objects.get(pk=account_id, is_active=True)
    except CompanyAccount.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Conta não encontrada.")}, status=404)

    account_type_id = request.POST.get("account_type", "").strip()
    name = request.POST.get("name", "").strip()
    account_identifier = request.POST.get("account_identifier", "").strip()
    balance_raw = request.POST.get("balance", "").strip()

    if not account_type_id or not name or not account_identifier:
        return JsonResponse(
            {"success": False, "message": _("Tipo de conta, nome e identificador são obrigatórios.")},
            status=400,
        )

    try:
        acc_type = AccountType.objects.get(pk=account_type_id, is_active=True)
    except AccountType.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Tipo de conta inválido.")}, status=400)

    # Saldo antes da alteração
    old_balance = account.balance or Decimal("0")

    # Calcular novo saldo
    try:
        if balance_raw != "":
            new_balance = Decimal(str(balance_raw))
        else:
            new_balance = old_balance
    except Exception:
        return JsonResponse({"success": False, "message": _("Saldo inválido.")}, status=400)

    # Actualizar campos da conta
    account.account_type = acc_type
    account.name = name
    account.account_identifier = account_identifier
    account.balance = new_balance
    account.save(update_fields=["account_type", "name", "account_identifier", "balance"])

    # Se o saldo mudou, registar transacção de ajuste manual
    if new_balance != old_balance:
        if new_balance > old_balance:
            tx_type = Transaction.TX_TYPE_IN
            amount = new_balance - old_balance
            desc = _("Ajuste manual de saldo (+{amount})").format(amount=amount)
        else:
            tx_type = Transaction.TX_TYPE_OUT
            amount = old_balance - new_balance
            desc = _("Ajuste manual de saldo (-{amount})").format(amount=amount)

        Transaction.objects.create(
            company_account=account,
            tx_type=tx_type,
            source_type="manual",
            source_id=None,
            tx_date=timezone.localdate(),
            description=desc,
            amount=amount,
            balance_before=old_balance,
            balance_after=new_balance,
            is_active=True,
            created_at=timezone.now(),
        )

    return JsonResponse({"success": True, "message": _("Conta actualizada com sucesso.")})



#============================================================================================================
#============================================================================================================
@require_POST
def deactivate_company_account(request, account_id):
    try:
        account = CompanyAccount.objects.get(pk=account_id, is_active=True)
    except CompanyAccount.DoesNotExist:
        return JsonResponse({"success": False, "message": _("Conta não encontrada.")}, status=404)

    account.is_active = False
    account.save(update_fields=["is_active"])

    return JsonResponse({"success": True, "message": _("Conta desactivada com sucesso.")})

#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================


#============================================================================================================
#============================================================================================================
