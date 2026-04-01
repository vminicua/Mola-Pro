from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from core.branding import (
    USER_CURRENCY_FORMAT_SESSION_KEY,
    USER_LANGUAGE_SESSION_KEY,
    load_brand_preferences,
    normalize_currency_format_key,
    normalize_language_code,
    save_brand_preferences,
)
from core.views.user.user_views import staff_required


@login_required
@staff_required
@require_http_methods(["GET"])
def preferences_view(request):
    return render(
        request,
        "preferences/preferences.html",
        {
            "segment": "preferences",
        },
    )


@login_required
@staff_required
@require_http_methods(["POST"])
def update_brand_preferences(request):
    try:
        preferences = save_brand_preferences(
            palette_key=request.POST.get("palette_key"),
            primary_color=request.POST.get("primary_color"),
            language=request.POST.get("language"),
            currency_format=request.POST.get("currency_format"),
            logo_file=request.FILES.get("logo"),
            remove_logo=request.POST.get("remove_logo") in {"1", "true", "on", "yes"},
            favicon_file=request.FILES.get("favicon"),
            remove_favicon=request.POST.get("remove_favicon") in {"1", "true", "on", "yes"},
        )
    except ValueError as exc:
        return JsonResponse(
            {
                "success": False,
                "message": str(exc),
            },
            status=400,
        )

    return JsonResponse(
        {
            "success": True,
            "currency_format": preferences["default_currency_format"],
            "currency_format_label": preferences["default_currency_format_label"],
            "message": _("Preferências actualizadas com sucesso."),
            "favicon_url": preferences["favicon_url"],
            "language": preferences["language"],
            "logo_url": preferences["logo_url"],
            "palette_key": preferences["palette_key"],
            "palette_label": preferences["palette"]["label"],
            "primary_color": preferences["primary_color"],
        }
    )


@login_required
@require_http_methods(["POST"])
def update_user_language(request):
    normalized_language = normalize_language_code(
        request.POST.get("language"),
        default=None,
    )
    if normalized_language is None:
        return JsonResponse(
            {
                "success": False,
                "message": _("Idioma inválido. Escolha Português (Moçambique) ou English."),
            },
            status=400,
        )

    default_preferences = load_brand_preferences()
    if normalized_language == default_preferences["default_language"]:
        request.session.pop(USER_LANGUAGE_SESSION_KEY, None)
    else:
        request.session[USER_LANGUAGE_SESSION_KEY] = normalized_language

    active_preferences = load_brand_preferences(language_override=normalized_language)

    return JsonResponse(
        {
            "success": True,
            "language": active_preferences["language"],
            "language_label": active_preferences["language_label"],
            "message": _("Idioma actualizado com sucesso."),
        }
    )


@login_required
@require_http_methods(["POST"])
def update_user_currency_format(request):
    normalized_currency_format = normalize_currency_format_key(
        request.POST.get("currency_format"),
        default=None,
    )
    if normalized_currency_format is None:
        return JsonResponse(
            {
                "success": False,
                "message": _("Formato monetário inválido. Escolha uma das opções disponíveis."),
            },
            status=400,
        )

    default_preferences = load_brand_preferences()
    if normalized_currency_format == default_preferences["default_currency_format"]:
        request.session.pop(USER_CURRENCY_FORMAT_SESSION_KEY, None)
    else:
        request.session[USER_CURRENCY_FORMAT_SESSION_KEY] = normalized_currency_format

    active_preferences = load_brand_preferences(currency_format_override=normalized_currency_format)

    return JsonResponse(
        {
            "success": True,
            "currency_format": active_preferences["currency_format"],
            "currency_format_example": active_preferences["currency_example"],
            "currency_format_label": active_preferences["currency_format_label"],
            "message": _("Formato monetário actualizado com sucesso."),
        }
    )
