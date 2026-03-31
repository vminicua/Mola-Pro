from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.models import Member, LoanType, InterestType, CompanyAccount, Loan, LoanGuarantor, LoanGuarantee, Transaction, LoanPaymentRequest
#============================================================================================================
#============================================================================================================

@login_required
@require_http_methods(["GET", "POST"])
def new_loan(request):
    members = Member.objects.filter(is_active=True).order_by("first_name", "last_name")
    loan_types = LoanType.objects.filter(is_active=True).order_by("name")
    interest_types = InterestType.objects.filter(is_active=True).order_by("name")
    company_accounts = CompanyAccount.objects.filter(is_active=True).order_by("name")

    errors = {}
    form_data = {}

    if request.method == "POST":
        member_id = request.POST.get("member", "").strip()
        loan_type_id = request.POST.get("loan_type", "").strip()
        interest_type_id = request.POST.get("interest_type", "").strip()
        principal_raw = request.POST.get("principal_amount", "").strip()
        term_raw = request.POST.get("term_periods", "").strip()
        period_type = request.POST.get("period_type", "monthly").strip()
        payment_raw = request.POST.get("payment_per_period", "").strip()

        release_date = request.POST.get("release_date") or None
        first_payment_date = request.POST.get("first_payment_date") or None

        disburse_method = request.POST.get("disburse_method", "cash").strip()
        company_account_id = request.POST.get("company_account", "").strip()

        purpose = request.POST.get("purpose", "").strip()
        remarks = request.POST.get("remarks", "").strip()
        
        guarantee_name = request.POST.get("guarantee_name", "").strip()
        guarantee_type = request.POST.get("guarantee_type", "").strip()
        guarantee_serial = request.POST.get("guarantee_serial", "").strip()
        guarantee_estimated_raw = request.POST.get("guarantee_estimated_price", "").strip()
        guarantee_attachment = request.FILES.get("guarantee_attachment")
        guarantee_description = request.POST.get("guarantee_description", "").strip()

        guarantor_member_id = request.POST.get("guarantor_member", "").strip()
        guarantor_account = request.POST.get("guarantor_account", "").strip()
        guarantor_amount_raw = request.POST.get("guarantor_amount", "").strip()

        attachment = request.FILES.get("attachment")

        form_data = request.POST.dict()

        # Validar member
        member = None
        if not member_id:
            errors["member"] = _("Selecione o membro/cliente.")
        else:
            try:
                member = members.get(pk=member_id)
            except Member.DoesNotExist:
                errors["member"] = _("Membro inválido.")

        # Validar interest_type
        interest_type = None
        if not interest_type_id:
            errors["interest_type"] = _("Selecione o tipo de juro.")
        else:
            try:
                interest_type = interest_types.get(pk=interest_type_id)
            except InterestType.DoesNotExist:
                errors["interest_type"] = _("Tipo de juro inválido.")

        # Loan type (opcional)
        loan_type = None
        if loan_type_id:
            try:
                loan_type = loan_types.get(pk=loan_type_id)
            except LoanType.DoesNotExist:
                errors["loan_type"] = _("Tipo de empréstimo inválido.")

        # Principal
        principal_amount = None
        if not principal_raw:
            errors["principal_amount"] = _("Informe o valor do empréstimo.")
        else:
            try:
                principal_amount = Decimal(str(principal_raw))
                if principal_amount <= 0:
                    raise ValueError
            except Exception:
                errors["principal_amount"] = _("Valor do empréstimo inválido.")

        # Term
        term_periods = None
        if not term_raw:
            errors["term_periods"] = _("Informe o número de períodos.")
        else:
            try:
                term_periods = int(term_raw)
                if term_periods <= 0:
                    raise ValueError
            except Exception:
                errors["term_periods"] = _("Número de períodos inválido.")

        # Payment per period
        payment_per_period = None
        if not payment_raw:
            errors["payment_per_period"] = _("Informe o pagamento por ciclo (pode usar o sugerido).")
        else:
            try:
                payment_per_period = Decimal(str(payment_raw))
                if payment_per_period <= 0:
                    raise ValueError
            except Exception:
                errors["payment_per_period"] = _("Pagamento por ciclo inválido.")

        # Disburse / conta
        company_account = None
        if disburse_method in ("company_account", "mobile_wallet"):
            if not company_account_id:
                errors["company_account"] = _("Selecione a conta da empresa usada para desembolso.")
            else:
                try:
                    company_account = company_accounts.get(pk=company_account_id)
                except CompanyAccount.DoesNotExist:
                    errors["company_account"] = _("Conta da empresa inválida.")

        # Se não houver erros -> criar Loan
        if not errors and member and interest_type and principal_amount and term_periods and payment_per_period:
            loan = Loan.objects.create(
                member=member,
                loan_type=loan_type,
                interest_type=interest_type,
                principal_amount=principal_amount,
                term_periods=term_periods,
                period_type=period_type,
                payment_per_period=payment_per_period,
                release_date=release_date,
                first_payment_date=first_payment_date,
                disburse_method=disburse_method,
                company_account=company_account,
                purpose=purpose or None,
                remarks=remarks or None,
                attachment=attachment,
                status="pending",
                created_by=request.user if request.user.is_authenticated else None,
            )
            
            # --- Garantias (opcional) ---
            has_guarantee_data = any([
                guarantee_name,
                guarantee_type,
                guarantee_serial,
                guarantee_estimated_raw,
                guarantee_attachment,
                guarantee_description,
            ])

            if has_guarantee_data:
                guarantee_estimated = None
                if guarantee_estimated_raw:
                    try:
                        guarantee_estimated = Decimal(str(guarantee_estimated_raw))
                    except Exception:
                        guarantee_estimated = None

                LoanGuarantee.objects.create(
                    loan=loan,
                    name=guarantee_name or "Garantia",
                    guarantee_type=guarantee_type or None,
                    serial_number=guarantee_serial or None,
                    estimated_price=guarantee_estimated,
                    attachment=guarantee_attachment,
                    description=guarantee_description or None,
                )

            # --- Avalista (opcional, precisa ser membro válido) ---
            if guarantor_member_id:
                try:
                    guarantor_member = Member.objects.get(pk=guarantor_member_id)
                except Member.DoesNotExist:
                    guarantor_member = None

                if guarantor_member:
                    guarantor_amount = None
                    if guarantor_amount_raw:
                        try:
                            guarantor_amount = Decimal(str(guarantor_amount_raw))
                        except Exception:
                            guarantor_amount = None

                    LoanGuarantor.objects.create(
                        loan=loan,
                        guarantor=guarantor_member,
                        account_number=guarantor_account or None,
                        amount=guarantor_amount,
                    )


            return render(
                request,
                "loan/new_loan.html",
                {
                    "members": members,
                    "segment": "loans_new",
                    "loan_types": loan_types,
                    "interest_types": interest_types,
                    "company_accounts": company_accounts,
                    "loan_created": True,
                    "new_loan_id": loan.id,
                },
            )

    return render(
        request,
        "loan/new_loan.html",
        {
            "members": members,
            "segment": "loans_new",
            "loan_types": loan_types,
            "interest_types": interest_types,
            "company_accounts": company_accounts,
            "errors": errors,
            "form_data": form_data,
        },
    )
#============================================================================================================
#============================================================================================================

def pending_loans_list(request):
    """
    Lista de empréstimos com status 'pending'.
    """
    loans = (
        Loan.objects
        .select_related("member", "loan_type", "interest_type", "created_by")
        .filter(status="pending")
        .order_by("-id")
    )
    context = {
        "loans": loans,
        "segment": "loans_pending",
    }
    
    return render(request, "loan/pending_loans_list.html", context)


#============================================================================================================
#============================================================================================================
@require_POST
def confirm_loan(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)

    if loan.status != "pending":
        return JsonResponse(
            {"success": False, "message": _("Apenas empréstimos pendentes podem ser confirmados.")},
            status=400,
        )

    loan.status = "approved"
    loan.approved_by = request.user         
    loan.save(update_fields=["status", "approved_by"])

    return JsonResponse(
        {"success": True, "message": _("Empréstimo confirmado. Agora pode ser desembolsado na secção Desembolso.")}
    )


#============================================================================================================
#============================================================================================================
@require_POST
def reject_loan(request, loan_id):
    """
    Rejeita um empréstimo pendente.
    Muda o status para 'cancelled'.
    """
    loan = get_object_or_404(Loan, pk=loan_id)

    if loan.status != "pending":
        return JsonResponse(
            {
                "success": False,
                "message": _("Apenas empréstimos pendentes podem ser rejeitados."),
            },
            status=400,
        )

    loan.status = "cancelled"
    loan.save(update_fields=["status"])

    return JsonResponse(
        {
            "success": True,
            "message": _("Empréstimo rejeitado com sucesso."),
        }
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
