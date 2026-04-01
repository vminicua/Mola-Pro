from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

from core.branding import (
    USER_CURRENCY_FORMAT_SESSION_KEY,
    USER_LANGUAGE_SESSION_KEY,
    load_brand_preferences,
    reset_active_brand_preferences,
    save_brand_preferences,
    set_active_brand_preferences,
)
from core.templatetags.core_i18n import format_money_value
from core.views.preferences_view import update_user_currency_format, update_user_language


class DummyAuthenticatedUser:
    is_authenticated = True


class BrandPalettePreferenceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.media_root = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name, MEDIA_URL="/media/")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media_root.cleanup)
        self.request_factory = RequestFactory()

    def _preferences_path(self) -> Path:
        return Path(self.media_root.name) / "preferences" / "branding.json"

    def _write_preferences(self, data: dict[str, str]) -> None:
        preferences_path = self._preferences_path()
        preferences_path.parent.mkdir(parents=True, exist_ok=True)
        preferences_path.write_text(json.dumps(data), encoding="utf-8")

    def test_load_brand_preferences_maps_legacy_primary_color_to_matching_palette(self) -> None:
        self._write_preferences(
            {
                "language": "en",
                "primary_color": "#42A5F5",
            }
        )

        preferences = load_brand_preferences()

        self.assertEqual(preferences["palette_key"], "ocean")
        self.assertEqual(preferences["primary_color"], "#42A5F5")
        self.assertEqual(preferences["palette"]["label"], "Atlantic Blue")

    def test_save_brand_preferences_persists_palette_key_and_primary_color(self) -> None:
        preferences = save_brand_preferences(
            palette_key="graphite",
            language="en",
            currency_format="intl",
        )
        stored_preferences = json.loads(self._preferences_path().read_text(encoding="utf-8"))

        self.assertEqual(preferences["palette_key"], "graphite")
        self.assertEqual(preferences["primary_color"], "#334155")
        self.assertEqual(preferences["default_currency_format"], "intl")
        self.assertEqual(stored_preferences["palette_key"], "graphite")
        self.assertEqual(stored_preferences["primary_color"], "#334155")
        self.assertEqual(stored_preferences["currency_format"], "intl")
        self.assertEqual(stored_preferences["language"], "en")

    def test_save_brand_preferences_rejects_unknown_palette(self) -> None:
        with self.assertRaisesMessage(ValueError, "Paleta inválida"):
            save_brand_preferences(palette_key="unknown-palette")

    def test_load_brand_preferences_supports_session_language_override(self) -> None:
        self._write_preferences(
            {
                "currency_format": "mz",
                "language": "pt-mz",
                "palette_key": "emerald",
            }
        )

        preferences = load_brand_preferences(language_override="en")

        self.assertEqual(preferences["language"], "en")
        self.assertEqual(preferences["default_language"], "pt-mz")
        self.assertTrue(preferences["is_language_overridden"])
        self.assertEqual(preferences["palette"]["label"], "Mola Green")

    def test_load_brand_preferences_defaults_to_mozambique_currency_format(self) -> None:
        preferences = load_brand_preferences()

        self.assertEqual(preferences["currency_format"], "mz")
        self.assertEqual(preferences["default_currency_format"], "mz")
        self.assertEqual(preferences["currency_example"], "100.000,00")

    def test_load_brand_preferences_supports_session_currency_override(self) -> None:
        self._write_preferences(
            {
                "currency_format": "mz",
                "language": "en",
                "palette_key": "emerald",
            }
        )

        preferences = load_brand_preferences(currency_format_override="intl")

        self.assertEqual(preferences["currency_format"], "intl")
        self.assertEqual(preferences["default_currency_format"], "mz")
        self.assertTrue(preferences["is_currency_format_overridden"])
        self.assertEqual(preferences["currency_thousands_separator"], ",")
        self.assertEqual(preferences["currency_decimal_separator"], ".")

    def test_format_money_value_uses_active_currency_format(self) -> None:
        preferences = load_brand_preferences(currency_format_override="intl")
        token = set_active_brand_preferences(preferences)
        self.addCleanup(reset_active_brand_preferences, token)

        self.assertEqual(format_money_value("100000.00"), "100,000.00")

    def test_update_user_language_stores_session_override(self) -> None:
        request = self.request_factory.post("/preferences/language/update/", {"language": "en"})
        SessionMiddleware(lambda _: None).process_request(request)
        request.user = DummyAuthenticatedUser()

        response = update_user_language(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session[USER_LANGUAGE_SESSION_KEY], "en")
        self.assertEqual(payload["language"], "en")

    def test_update_user_currency_format_stores_session_override(self) -> None:
        request = self.request_factory.post(
            "/preferences/currency-format/update/",
            {"currency_format": "intl"},
        )
        SessionMiddleware(lambda _: None).process_request(request)
        request.user = DummyAuthenticatedUser()

        response = update_user_currency_format(request)
        payload = json.loads(response.content.decode("utf-8"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.session[USER_CURRENCY_FORMAT_SESSION_KEY], "intl")
        self.assertEqual(payload["currency_format"], "intl")
