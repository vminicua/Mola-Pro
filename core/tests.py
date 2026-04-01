from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from core.branding import load_brand_preferences, save_brand_preferences


class BrandPalettePreferenceTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.media_root = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root.name, MEDIA_URL="/media/")
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.media_root.cleanup)

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
        preferences = save_brand_preferences(palette_key="graphite", language="en")
        stored_preferences = json.loads(self._preferences_path().read_text(encoding="utf-8"))

        self.assertEqual(preferences["palette_key"], "graphite")
        self.assertEqual(preferences["primary_color"], "#334155")
        self.assertEqual(stored_preferences["palette_key"], "graphite")
        self.assertEqual(stored_preferences["primary_color"], "#334155")
        self.assertEqual(stored_preferences["language"], "en")

    def test_save_brand_preferences_rejects_unknown_palette(self) -> None:
        with self.assertRaisesMessage(ValueError, "Paleta inválida"):
            save_brand_preferences(palette_key="unknown-palette")
