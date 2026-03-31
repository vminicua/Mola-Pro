from core.branding import load_brand_preferences


def brand_preferences(request):
    preferences = getattr(request, "brand_preferences", None) or load_brand_preferences()
    return {
        "brand_preferences": preferences,
    }
