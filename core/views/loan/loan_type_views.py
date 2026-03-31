from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _

from core.models import LoanType

#============================================================================================================
#============================================================================================================
def loan_type_list(request):
    """
    Página principal: lista Tipos de Empréstimos num DataTable
    + botão para adicionar / editar / activar / desactivar.
    """
    loan_types = LoanType.objects.all().order_by("name")
    context = {
        "loan_types": loan_types,
        "segment": "loan_types",
    }
    return render(request, "loan/loan_type_list.html", context)

#============================================================================================================
#============================================================================================================
@require_POST
def create_loan_type(request):
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse(
            {"success": False, "message": _("O nome do tipo de empréstimo é obrigatório.")},
            status=400,
        )

    LoanType.objects.create(
        name=name,
        description=description or None,
        is_active=True,
    )

    return JsonResponse({"success": True, "message": _("Tipo de empréstimo criado com sucesso.")})
#============================================================================================================
#============================================================================================================

@require_POST
def update_loan_type(request, type_id):
    loan_type = get_object_or_404(LoanType, pk=type_id)

    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()

    if not name:
        return JsonResponse(
            {"success": False, "message": _("O nome do tipo de empréstimo é obrigatório.")},
            status=400,
        )

    loan_type.name = name
    loan_type.description = description or None
    loan_type.save(update_fields=["name", "description"])

    return JsonResponse({"success": True, "message": _("Tipo de empréstimo actualizado com sucesso.")})

#============================================================================================================
#============================================================================================================
@require_POST
def toggle_loan_type(request, type_id):
    """
    Activa / desactiva o tipo de empréstimo.
    """
    loan_type = get_object_or_404(LoanType, pk=type_id)
    loan_type.is_active = not loan_type.is_active
    loan_type.save(update_fields=["is_active"])

    status_label = _("activado") if loan_type.is_active else _("desactivado")
    return JsonResponse(
        {"success": True, "message": _("Tipo de empréstimo {status_label} com sucesso.").format(status_label=status_label)}
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
