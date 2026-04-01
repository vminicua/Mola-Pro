from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from core.branding import save_brand_preferences
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
            "message": _("Preferências actualizadas com sucesso."),
            "favicon_url": preferences["favicon_url"],
            "language": preferences["language"],
            "logo_url": preferences["logo_url"],
            "palette_key": preferences["palette_key"],
            "palette_label": preferences["palette"]["label"],
            "primary_color": preferences["primary_color"],
        }
    )
