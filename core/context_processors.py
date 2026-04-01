from core.branding import get_active_brand_preferences


def brand_preferences(request):
    preferences = getattr(request, "brand_preferences", None) or get_active_brand_preferences()
    return {
        "brand_preferences": preferences,
    }
