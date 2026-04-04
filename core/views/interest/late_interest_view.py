from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.models import LateInterestSetting


def _ensure_late_interest_settings():
    defaults = {
        LateInterestSetting.PERIOD_DAILY: Decimal("0.0000"),
        LateInterestSetting.PERIOD_MONTHLY: Decimal("0.0000"),
    }

    settings_map = {}
    for period_type, rate in defaults.items():
        settings_map[period_type], _created = LateInterestSetting.objects.get_or_create(
            period_type=period_type,
            defaults={"rate": rate},
        )

    return settings_map


@login_required
def late_interest_settings_list(request):
    settings_map = _ensure_late_interest_settings()
    ordered_settings = [
        settings_map[LateInterestSetting.PERIOD_DAILY],
        settings_map[LateInterestSetting.PERIOD_MONTHLY],
    ]

    return render(
        request,
        "interest/late_interest_settings.html",
        {
            "segment": "late_interest_settings",
            "late_interest_settings": ordered_settings,
        },
    )


@login_required
@require_POST
def update_late_interest_setting(request):
    setting_id = request.POST.get("id", "").strip()
    rate_raw = request.POST.get("rate", "").strip()

    if not setting_id:
        return JsonResponse(
            {"success": False, "message": _("ID da configuração é obrigatório.")},
            status=400,
        )

    if not rate_raw:
        return JsonResponse(
            {"success": False, "message": _("A percentagem de juros de mora é obrigatória.")},
            status=400,
        )

    try:
        rate = Decimal(str(rate_raw))
    except Exception:
        return JsonResponse(
            {"success": False, "message": _("Percentagem de juros de mora inválida.")},
            status=400,
        )

    if rate < 0:
        return JsonResponse(
            {"success": False, "message": _("A percentagem de juros de mora não pode ser negativa.")},
            status=400,
        )

    late_interest_setting = get_object_or_404(LateInterestSetting, pk=setting_id)
    late_interest_setting.rate = rate
    late_interest_setting.save(update_fields=["rate", "updated_at"])

    return JsonResponse(
        {
            "success": True,
            "message": _("Juros de mora {period_label} actualizados com sucesso.").format(
                period_label=late_interest_setting.get_period_type_display().lower()
            ),
        }
    )
