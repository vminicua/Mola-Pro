from django.utils import translation

from core.branding import (
    USER_CURRENCY_FORMAT_SESSION_KEY,
    USER_LANGUAGE_SESSION_KEY,
    load_brand_preferences,
    reset_active_brand_preferences,
    set_active_brand_preferences,
)


class BrandPreferenceLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_language = None
        session_currency_format = None
        if hasattr(request, "session"):
            session_language = request.session.get(USER_LANGUAGE_SESSION_KEY)
            session_currency_format = request.session.get(USER_CURRENCY_FORMAT_SESSION_KEY)

        preferences = load_brand_preferences(
            language_override=session_language,
            currency_format_override=session_currency_format,
        )
        request.brand_preferences = preferences
        request.app_language = preferences["language"]
        request.app_currency_format = preferences["currency_format"]
        context_token = set_active_brand_preferences(preferences)

        translation.activate(preferences["translation_language"])
        request.LANGUAGE_CODE = preferences["translation_language"]

        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()
            reset_active_brand_preferences(context_token)

        response.headers.setdefault("Content-Language", preferences["language"])
        return response
