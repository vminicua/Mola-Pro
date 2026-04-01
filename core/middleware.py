from django.utils import translation

from core.branding import USER_LANGUAGE_SESSION_KEY, load_brand_preferences


class BrandPreferenceLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_language = None
        if hasattr(request, "session"):
            session_language = request.session.get(USER_LANGUAGE_SESSION_KEY)

        preferences = load_brand_preferences(language_override=session_language)
        request.brand_preferences = preferences
        request.app_language = preferences["language"]

        translation.activate(preferences["translation_language"])
        request.LANGUAGE_CODE = preferences["translation_language"]

        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()

        response.headers.setdefault("Content-Language", preferences["language"])
        return response
