from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.utils.translation import gettext as _

from core.models import InterestType


#============================================================================================================
#============================================================================================================
def interest_type_list(request):
    interest_types = InterestType.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "interest/interest_type_list.html",
        {"interest_types": interest_types,
         "segment": "interest_types",},
    )


#============================================================================================================
#============================================================================================================
@require_POST
def create_interest_type(request):
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    rate_raw = request.POST.get("rate", "").strip()
    period_type = request.POST.get("period_type", "").strip()
    calculation_method = request.POST.get("calculation_method", "flat").strip() or "flat"

    if not name or not rate_raw or not period_type:
        return JsonResponse(
            {
                "success": False,
                "message": _("Nome, taxa e tipo de período são obrigatórios."),
            },
            status=400,
        )

    if period_type not in ("monthly", "daily"):
        return JsonResponse(
            {"success": False, "message": _("Tipo de período inválido.")},
            status=400,
        )

    try:
        rate = Decimal(str(rate_raw))
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Taxa de juro inválida.")},
            status=400,
        )

    InterestType.objects.create(
        name=name,
        description=description or None,
        rate=rate,
        period_type=period_type,
        calculation_method=calculation_method,
        is_active=True,
    )

    return JsonResponse(
        {"success": True, "message": _("Tipo de juro criado com sucesso.")}
    )


#============================================================================================================
#============================================================================================================
def interest_calculator(request):
    interest_types = InterestType.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "interest/interest_calculator.html",
        {"interest_types": interest_types,
         "segment": "interest_calculator",},
    )



#============================================================================================================
#============================================================================================================

#============================================================================================================
#==================================== EDITAR TIPO DE JURO ===================================================
#============================================================================================================
@require_POST
def update_interest_type(request):
    it_id = request.POST.get("id", "").strip()
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    rate_raw = request.POST.get("rate", "").strip()
    period_type = request.POST.get("period_type", "").strip()
    calculation_method = request.POST.get("calculation_method", "flat").strip() or "flat"

    if not it_id:
        return JsonResponse(
            {"success": False, "message": _("ID do tipo de juro é obrigatório.")},
            status=400,
        )

    if not name or not rate_raw or not period_type:
        return JsonResponse(
            {
                "success": False,
                "message": _("Nome, taxa e tipo de período são obrigatórios."),
            },
            status=400,
        )

    if period_type not in ("monthly", "daily"):
        return JsonResponse(
            {"success": False, "message": _("Tipo de período inválido.")},
            status=400,
        )

    try:
        rate = Decimal(str(rate_raw))
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Taxa de juro inválida.")},
            status=400,
        )

    interest_type = get_object_or_404(InterestType, pk=it_id)

    interest_type.name = name
    interest_type.description = description or None
    interest_type.rate = rate
    interest_type.period_type = period_type
    interest_type.calculation_method = calculation_method
    interest_type.save(
        update_fields=["name", "description", "rate", "period_type", "calculation_method"]
    )

    return JsonResponse(
        {"success": True, "message": _("Tipo de juro actualizado com sucesso.")}
    )


#============================================================================================================
#============================= ACTIVAR / DESACTIVAR TIPO DE JURO ============================================
#============================================================================================================
@require_POST
def toggle_interest_type_status(request):
    it_id = request.POST.get("id", "").strip()

    if not it_id:
        return JsonResponse(
            {"success": False, "message": _("ID do tipo de juro é obrigatório.")},
            status=400,
        )

    interest_type = get_object_or_404(InterestType, pk=it_id)

    interest_type.is_active = not interest_type.is_active
    interest_type.save(update_fields=["is_active"])

    status_label = _("activado") if interest_type.is_active else _("desactivado")

    return JsonResponse(
        {
            "success": True,
            "message": _("Tipo de juro {status_label} com sucesso.").format(status_label=status_label),
            "is_active": interest_type.is_active,
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
