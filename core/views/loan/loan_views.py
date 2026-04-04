from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST, require_http_methods

from core.loan_math import calculate_flat_loan_metrics
from core.models import InterestType, Loan, LoanDocument, LoanGuarantee, LoanGuarantor, LoanType, Member
#============================================================================================================
#============================================================================================================


def _add_months(base_date: date, months: int = 1) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def _build_new_loan_form_defaults(loan_types, interest_types):
    release_date = timezone.localdate()
    first_payment_date = _add_months(release_date, 1)
    default_loan_type = loan_types.first()
    default_interest_type = interest_types.first()

    return {
        "loan_type": str(default_loan_type.id) if default_loan_type else "",
        "interest_type": str(default_interest_type.id) if default_interest_type else "",
        "term_periods": "1",
        "period_type": "monthly",
        "release_date": release_date.isoformat(),
        "first_payment_date": first_payment_date.isoformat(),
    }


def _parse_form_date(raw_value):
    if not raw_value:
        return None

    parsed_value = parse_date(raw_value)
    return parsed_value


def _build_guarantee_rows(post_data=None):
    if post_data is None:
        return [{
            "name": "",
            "guarantee_type": "",
            "serial_number": "",
            "estimated_price": "",
            "description": "",
        }]

    names = post_data.getlist("guarantee_name[]")
    guarantee_types = post_data.getlist("guarantee_type[]")
    serial_numbers = post_data.getlist("guarantee_serial[]")
    estimated_prices = post_data.getlist("guarantee_estimated_price[]")
    descriptions = post_data.getlist("guarantee_description[]")
    total_rows = max(len(names), len(guarantee_types), len(serial_numbers), len(estimated_prices), len(descriptions), 1)

    rows = []
    for index in range(total_rows):
        rows.append({
            "name": names[index] if index < len(names) else "",
            "guarantee_type": guarantee_types[index] if index < len(guarantee_types) else "",
            "serial_number": serial_numbers[index] if index < len(serial_numbers) else "",
            "estimated_price": estimated_prices[index] if index < len(estimated_prices) else "",
            "description": descriptions[index] if index < len(descriptions) else "",
        })

    return rows


def _build_guarantor_rows(post_data=None):
    if post_data is None:
        return [{"member_id": ""}]

    member_ids = post_data.getlist("guarantor_member[]")
    total_rows = max(len(member_ids), 1)
    return [
        {
            "member_id": member_ids[index] if index < len(member_ids) else "",
        }
        for index in range(total_rows)
    ]


def _calculate_due_date(base_date, period_type, offset):
    if not base_date:
        return None

    if period_type == "daily":
        return base_date + timedelta(days=offset)

    return _add_months(base_date, offset)


def _build_loan_schedule_rows(loan):
    metrics = calculate_flat_loan_metrics(
        loan.principal_amount,
        getattr(loan.interest_type, "rate", Decimal("0")) or Decimal("0"),
        loan.term_periods,
    )
    base_payment = loan.payment_per_period or metrics["suggested_payment_per_period"]
    remaining_principal = metrics["principal"]
    remaining_total = metrics["total_to_repay"]
    due_base = loan.first_payment_date

    if not due_base and loan.release_date:
        due_base = loan.release_date + timedelta(days=1) if loan.period_type == "daily" else _add_months(loan.release_date, 1)

    rows = []
    for installment_number in range(1, metrics["periods"] + 1):
        if remaining_total <= Decimal("0.00"):
            break

        payment = remaining_total if installment_number == metrics["periods"] or remaining_total <= base_payment else base_payment
        payment = Decimal(str(payment)).quantize(Decimal("0.01"))
        interest = metrics["interest_per_period"]
        principal_reduction = min(remaining_principal, max(payment - interest, Decimal("0.00"))).quantize(Decimal("0.01"))
        principal_before = remaining_principal
        remaining_principal = max(remaining_principal - principal_reduction, Decimal("0.00")).quantize(Decimal("0.01"))
        remaining_total = max(remaining_total - payment, Decimal("0.00")).quantize(Decimal("0.01"))

        note = _("Prestação regular.")
        if payment <= interest:
            note = _("Prestação abaixo dos juros do período; ajuste final aplicado depois.")
        elif payment != base_payment or installment_number == metrics["periods"]:
            note = _("Prestação ajustada para encerrar o empréstimo.")

        rows.append({
            "installment_number": installment_number,
            "period_label": _("Dia {number}").format(number=installment_number)
                if loan.period_type == "daily"
                else _("Mês {number}").format(number=installment_number),
            "due_date": _calculate_due_date(due_base, loan.period_type, installment_number - 1),
            "principal_before": principal_before,
            "interest": interest,
            "payment": payment,
            "principal_reduction": principal_reduction,
            "remaining_principal": remaining_principal,
            "note": note,
        })

    return metrics, rows


def _pdf_error_response(request, loan, message, status):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "message": message}, status=status)

    return redirect(f"{reverse('core:loan_list_all')}?status={loan.status}&pdf_error=1&loan_id={loan.id}")


def _can_manage_pending_loans(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.groups.filter(id=1).exists()))


def _is_truthy_value(raw_value):
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _build_loan_document_name(filename):
    document_name = Path(filename or "").stem.replace("_", " ").replace("-", " ").strip()
    return (document_name or _("Documento do empréstimo"))[:180]


def _infer_loan_document_type(filename):
    lowered_name = (filename or "").lower()
    extension = Path(filename or "").suffix.lower()

    if "contrat" in lowered_name:
        return _("Contrato")

    if extension in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return _("Imagem")

    return _("Outro documento")


@login_required
@require_http_methods(["GET", "POST"])
def new_loan(request):
    members = Member.objects.filter(is_active=True).order_by("first_name", "last_name")
    loan_types = LoanType.objects.filter(is_active=True).order_by("name")
    interest_types = InterestType.objects.filter(is_active=True).order_by("name")

    errors = {}
    form_data = _build_new_loan_form_defaults(loan_types, interest_types)
    guarantee_rows = _build_guarantee_rows()
    guarantor_rows = _build_guarantor_rows()

    if request.method == "POST":
        member_id = request.POST.get("member", "").strip()
        loan_type_id = request.POST.get("loan_type", "").strip()
        interest_type_id = request.POST.get("interest_type", "").strip()
        principal_raw = request.POST.get("principal_amount", "").strip()
        term_raw = request.POST.get("term_periods", "").strip()
        period_type = request.POST.get("period_type", "monthly").strip()
        payment_raw = request.POST.get("payment_per_period", "").strip()
        release_date_raw = request.POST.get("release_date") or None
        first_payment_date_raw = request.POST.get("first_payment_date") or None
        purpose = request.POST.get("purpose", "").strip()
        remarks = request.POST.get("remarks", "").strip()

        form_data.update(request.POST.dict())
        guarantee_rows = _build_guarantee_rows(request.POST)
        guarantor_rows = _build_guarantor_rows(request.POST)

        member = None
        if not member_id:
            errors["member"] = _("Selecione o cliente.")
        else:
            try:
                member = members.get(pk=member_id)
            except Member.DoesNotExist:
                errors["member"] = _("Cliente inválido.")

        interest_type = None
        if not interest_type_id:
            errors["interest_type"] = _("Selecione o tipo de juro.")
        else:
            try:
                interest_type = interest_types.get(pk=interest_type_id)
            except InterestType.DoesNotExist:
                errors["interest_type"] = _("Tipo de juro inválido.")

        loan_type = None
        if loan_type_id:
            try:
                loan_type = loan_types.get(pk=loan_type_id)
            except LoanType.DoesNotExist:
                errors["loan_type"] = _("Tipo de empréstimo inválido.")

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

        release_date = _parse_form_date(release_date_raw)
        if not release_date_raw:
            errors["release_date"] = _("Informe a data de libertação.")
        elif release_date is None:
            errors["release_date"] = _("Data de libertação inválida.")

        first_payment_date = _parse_form_date(first_payment_date_raw)
        if not first_payment_date_raw:
            errors["first_payment_date"] = _("Informe a data de pagamento.")
        elif first_payment_date is None:
            errors["first_payment_date"] = _("Data de pagamento inválida.")

        if release_date and first_payment_date and first_payment_date < release_date:
            errors["first_payment_date"] = _("A data de pagamento não pode ser anterior à data de libertação.")

        guarantee_payloads = []
        for index, row in enumerate(guarantee_rows, start=1):
            has_data = any([
                (row.get("name") or "").strip(),
                (row.get("guarantee_type") or "").strip(),
                (row.get("serial_number") or "").strip(),
                (row.get("estimated_price") or "").strip(),
                (row.get("description") or "").strip(),
            ])
            if not has_data:
                continue

            estimated_price = None
            estimated_price_raw = (row.get("estimated_price") or "").strip()
            if estimated_price_raw:
                try:
                    estimated_price = Decimal(str(estimated_price_raw))
                except Exception:
                    errors["guarantees"] = _("Valor estimado inválido na garantia {index}.").format(index=index)
                    break

            guarantee_payloads.append({
                "name": (row.get("name") or "").strip() or _("Garantia {index}").format(index=index),
                "guarantee_type": (row.get("guarantee_type") or "").strip() or None,
                "serial_number": (row.get("serial_number") or "").strip() or None,
                "estimated_price": estimated_price,
                "description": (row.get("description") or "").strip() or None,
            })

        guarantor_payloads = []
        if "guarantees" not in errors:
            selected_guarantor_ids = [row["member_id"] for row in guarantor_rows if row.get("member_id")]
            guarantor_map = {
                str(guarantor.id): guarantor
                for guarantor in members.filter(pk__in=selected_guarantor_ids)
            }

            for index, row in enumerate(guarantor_rows, start=1):
                member_value = (row.get("member_id") or "").strip()
                if not member_value:
                    continue

                guarantor_member = guarantor_map.get(member_value)
                if guarantor_member is None:
                    errors["guarantors"] = _("Avalista inválido na linha {index}.").format(index=index)
                    break

                guarantor_payloads.append({
                    "guarantor": guarantor_member,
                })

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
                disburse_method="cash",
                company_account=None,
                purpose=purpose or None,
                remarks=remarks or None,
                status="pending",
                created_by=request.user if request.user.is_authenticated else None,
            )

            for guarantee_payload in guarantee_payloads:
                LoanGuarantee.objects.create(
                    loan=loan,
                    name=guarantee_payload["name"],
                    guarantee_type=guarantee_payload["guarantee_type"],
                    serial_number=guarantee_payload["serial_number"],
                    estimated_price=guarantee_payload["estimated_price"],
                    description=guarantee_payload["description"],
                )

            for guarantor_payload in guarantor_payloads:
                LoanGuarantor.objects.create(
                    loan=loan,
                    guarantor=guarantor_payload["guarantor"],
                    account_number=None,
                    amount=None,
                )

            return redirect(f"{reverse('core:loan_list_all')}?status=pending&created=1&loan_id={loan.id}")

    return render(
        request,
        "loan/new_loan.html",
        {
            "members": members,
            "segment": "loans_new",
            "loan_types": loan_types,
            "interest_types": interest_types,
            "errors": errors,
            "form_data": form_data,
            "guarantee_rows": guarantee_rows,
            "guarantor_rows": guarantor_rows,
        },
    )
#============================================================================================================
#============================================================================================================


@login_required
def download_loan_pdf(request, loan_id):
    loan = get_object_or_404(
        Loan.objects.select_related("member", "loan_type", "interest_type", "approved_by", "created_by").prefetch_related(
            "guarantees",
            "loan_guarantors",
            "loan_guarantors__guarantor",
        ),
        pk=loan_id,
    )

    try:
        from weasyprint import HTML
    except Exception:
        return _pdf_error_response(
            request,
            loan,
            _("Não foi possível gerar o PDF. Verifique se o WeasyPrint está configurado no servidor."),
            503,
        )

    try:
        metrics, schedule_rows = _build_loan_schedule_rows(loan)
        context = {
            "loan": loan,
            "member": loan.member,
            "metrics": metrics,
            "schedule_rows": schedule_rows,
            "guarantees": loan.guarantees.all(),
            "guarantors": loan.loan_guarantors.select_related("guarantor"),
            "generated_at": timezone.localtime(),
        }

        html_string = render_to_string("loan/loan_receipt_pdf.html", context, request=request)
        html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
        pdf_bytes = html.write_pdf()
    except Exception:
        return _pdf_error_response(
            request,
            loan,
            _("Falha ao gerar o PDF do empréstimo."),
            500,
        )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="emprestimo_{loan.id}.pdf"'
    return response
#============================================================================================================
#============================================================================================================

@login_required
def pending_loans_list(request):
    """
    Rota legada.
    Redirecciona para a listagem única de empréstimos filtrada por pendentes.
    """
    return redirect(f"{reverse('core:loan_list_all')}?status=pending")


#============================================================================================================
#============================================================================================================
@login_required
@require_POST
def confirm_loan(request, loan_id):
    if not _can_manage_pending_loans(request.user):
        return JsonResponse(
            {"success": False, "message": _("Não tem permissão para aprovar empréstimos.")},
            status=403,
        )

    loan = get_object_or_404(Loan, pk=loan_id)

    if loan.status != "pending":
        return JsonResponse(
            {"success": False, "message": _("Apenas empréstimos pendentes podem ser confirmados.")},
            status=400,
        )

    late_interest_enabled = _is_truthy_value(request.POST.get("late_interest_enabled"))
    document_files = request.FILES.getlist("documents[]")

    with transaction.atomic():
        loan.status = "approved"
        loan.approved_by = request.user
        loan.late_interest_enabled = late_interest_enabled
        loan.save(update_fields=["status", "approved_by", "late_interest_enabled"])

        documents_count = 0
        for document_file in document_files:
            if not document_file:
                continue

            LoanDocument.objects.create(
                loan=loan,
                name=_build_loan_document_name(document_file.name),
                document_type=_infer_loan_document_type(document_file.name),
                file=document_file,
                uploaded_by=request.user if request.user.is_authenticated else None,
            )
            documents_count += 1

    message_parts = [
        _("Empréstimo confirmado. Agora pode ser desembolsado na secção Desembolso.")
    ]
    if late_interest_enabled:
        message_parts.append(_("Juros de mora activados para este empréstimo."))
    if documents_count == 1:
        message_parts.append(_("1 documento anexado."))
    elif documents_count > 1:
        message_parts.append(_("{count} documentos anexados.").format(count=documents_count))

    return JsonResponse(
        {
            "success": True,
            "message": " ".join(message_parts),
            "late_interest_enabled": late_interest_enabled,
            "documents_count": documents_count,
        }
    )


#============================================================================================================
#============================================================================================================
@login_required
@require_POST
def reject_loan(request, loan_id):
    """
    Rejeita um empréstimo pendente.
    Muda o status para 'cancelled'.
    """
    if not _can_manage_pending_loans(request.user):
        return JsonResponse(
            {"success": False, "message": _("Não tem permissão para rejeitar empréstimos.")},
            status=403,
        )

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
