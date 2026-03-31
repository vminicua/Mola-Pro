from core.branding import load_brand_preferences


def brand_preferences(request):
    return {
        "brand_preferences": load_brand_preferences(),
    }
