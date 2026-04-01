from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.storage import default_storage
from django.templatetags.static import static
from django.utils.translation import gettext as _


DEFAULT_BRAND_NAME = "Mola Pro"
DEFAULT_PRIMARY_COLOR = "#064E3B"
DEFAULT_LANGUAGE = "pt-mz"
DEFAULT_PALETTE_KEY = "emerald"
PREFERENCES_RELATIVE_PATH = "preferences/branding.json"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
ALLOWED_FAVICON_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
LANGUAGE_OPTIONS: dict[str, dict[str, str]] = {
    "pt-mz": {
        "label": "Português (Moçambique)",
        "translation_code": "pt",
        "datatables_language_url": "https://cdn.datatables.net/plug-ins/1.13.8/i18n/pt-PT.json",
    },
    "en": {
        "label": "English",
        "translation_code": "en",
        "datatables_language_url": "https://cdn.datatables.net/plug-ins/1.13.8/i18n/en-GB.json",
    },
}
LANGUAGE_ALIASES = {
    "pt": "pt-mz",
    "pt-mz": "pt-mz",
    "pt_mz": "pt-mz",
    "pt-pt": "pt-mz",
    "en": "en",
    "en-us": "en",
    "en_us": "en",
    "en-gb": "en",
    "en_gb": "en",
}
PALETTE_COLOR_ROLES = ("primary", "secondary", "info", "success", "warning", "danger")
BRAND_PALETTE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "emerald": {
        "label": {
            "pt": "Verde Mola",
            "en": "Mola Green",
        },
        "description": {
            "pt": "Uma base elegante e confiante, com verde profundo e apoio em tons frios.",
            "en": "A confident, elegant base with a deep green primary and cool supporting tones.",
        },
        "colors": {
            "primary": "#064E3B",
            "secondary": "#0F766E",
            "info": "#0284C7",
            "success": "#16A34A",
            "warning": "#D97706",
            "danger": "#DC2626",
        },
    },
    "ocean": {
        "label": {
            "pt": "Azul Atlântico",
            "en": "Atlantic Blue",
        },
        "description": {
            "pt": "Uma paleta clara e moderna, ideal para transmitir agilidade e transparência.",
            "en": "A clear, modern palette that feels agile and transparent.",
        },
        "colors": {
            "primary": "#42A5F5",
            "secondary": "#1D4ED8",
            "info": "#0891B2",
            "success": "#10B981",
            "warning": "#F59E0B",
            "danger": "#EF4444",
        },
    },
    "terracotta": {
        "label": {
            "pt": "Terracota Solar",
            "en": "Solar Terracotta",
        },
        "description": {
            "pt": "Mistura calor, proximidade e energia, com bom contraste para CTAs.",
            "en": "Blends warmth, energy, and strong CTA contrast.",
        },
        "colors": {
            "primary": "#C2410C",
            "secondary": "#9A3412",
            "info": "#0369A1",
            "success": "#15803D",
            "warning": "#EA580C",
            "danger": "#BE123C",
        },
    },
    "indigo": {
        "label": {
            "pt": "Índigo Financeiro",
            "en": "Finance Indigo",
        },
        "description": {
            "pt": "Passa uma imagem mais institucional, com um toque tecnológico.",
            "en": "Feels more institutional while keeping a subtle tech edge.",
        },
        "colors": {
            "primary": "#4338CA",
            "secondary": "#312E81",
            "info": "#0EA5E9",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "danger": "#E11D48",
        },
    },
    "graphite": {
        "label": {
            "pt": "Grafite Dourado",
            "en": "Golden Graphite",
        },
        "description": {
            "pt": "Um visual corporativo e sóbrio, com neutros fortes e destaque dourado.",
            "en": "A sober corporate look with strong neutrals and warm golden emphasis.",
        },
        "colors": {
            "primary": "#334155",
            "secondary": "#0F172A",
            "info": "#0284C7",
            "success": "#16A34A",
            "warning": "#CA8A04",
            "danger": "#DC2626",
        },
    },
}


def _preferences_file_path() -> Path:
    return Path(settings.MEDIA_ROOT) / PREFERENCES_RELATIVE_PATH


def _read_preferences() -> dict[str, Any]:
    preferences_path = _preferences_file_path()
    if not preferences_path.exists():
        return {}

    try:
        with preferences_path.open("r", encoding="utf-8") as preferences_file:
            data = json.load(preferences_file)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _write_preferences(data: dict[str, Any]) -> None:
    preferences_path = _preferences_file_path()
    preferences_path.parent.mkdir(parents=True, exist_ok=True)
    with preferences_path.open("w", encoding="utf-8") as preferences_file:
        json.dump(data, preferences_file, ensure_ascii=True, indent=2, sort_keys=True)


def normalize_language_code(value: str | None, default: str | None = DEFAULT_LANGUAGE) -> str | None:
    candidate = (value or "").strip().lower()
    if not candidate:
        return default

    return LANGUAGE_ALIASES.get(candidate, default)


def get_language_definition(value: str | None) -> dict[str, str]:
    normalized = normalize_language_code(value, default=DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
    return LANGUAGE_OPTIONS[normalized]


def get_translation_language_code(value: str | None) -> str:
    return get_language_definition(value)["translation_code"]


def get_available_languages() -> list[dict[str, str]]:
    return [
        {
            "code": code,
            "label": config["label"],
        }
        for code, config in LANGUAGE_OPTIONS.items()
    ]


def normalize_hex_color(value: str | None, default: str = DEFAULT_PRIMARY_COLOR) -> str:
    candidate = (value or "").strip().upper()
    if not candidate:
        return default

    if not candidate.startswith("#"):
        candidate = f"#{candidate}"

    if re.fullmatch(r"#[0-9A-F]{6}", candidate):
        return candidate

    return default


def is_valid_hex_color(value: str | None) -> bool:
    candidate = (value or "").strip().upper()
    if not candidate:
        return False

    if not candidate.startswith("#"):
        candidate = f"#{candidate}"

    return re.fullmatch(r"#[0-9A-F]{6}", candidate) is not None


def normalize_palette_key(value: str | None, default: str | None = DEFAULT_PALETTE_KEY) -> str | None:
    candidate = (value or "").strip().lower()
    if not candidate:
        return default

    if candidate in BRAND_PALETTE_DEFINITIONS:
        return candidate

    return default


def is_valid_palette_key(value: str | None) -> bool:
    return normalize_palette_key(value, default=None) is not None


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = normalize_hex_color(value)
    return tuple(int(normalized[index:index + 2], 16) for index in (1, 3, 5))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _mix(rgb: tuple[int, int, int], target: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    clamped_ratio = max(0.0, min(1.0, ratio))
    return tuple(
        max(0, min(255, round(channel + (target_channel - channel) * clamped_ratio)))
        for channel, target_channel in zip(rgb, target)
    )


def _build_color_family(prefix: str, color: str) -> dict[str, str]:
    normalized = normalize_hex_color(color)
    rgb = _hex_to_rgb(normalized)
    brightness = sum(rgb) / 3

    hover_rgb = _mix(
        rgb,
        (255, 255, 255) if brightness < 110 else (0, 0, 0),
        0.12 if brightness < 110 else 0.08,
    )
    strong_rgb = _mix(rgb, (0, 0, 0), 0.08 if brightness < 90 else 0.18)
    soft_rgb = _mix(rgb, (255, 255, 255), 0.88)
    soft_2_rgb = _mix(rgb, (255, 255, 255), 0.94)
    light_rgb = _mix(rgb, (255, 255, 255), 0.55)
    light_2_rgb = _mix(rgb, (255, 255, 255), 0.72)

    return {
        prefix: normalized,
        f"{prefix}_rgb": ", ".join(str(channel) for channel in rgb),
        f"{prefix}_hover": _rgb_to_hex(hover_rgb),
        f"{prefix}_hover_rgb": ", ".join(str(channel) for channel in hover_rgb),
        f"{prefix}_active": normalized,
        f"{prefix}_active_rgb": ", ".join(str(channel) for channel in rgb),
        f"{prefix}_strong": _rgb_to_hex(strong_rgb),
        f"{prefix}_strong_rgb": ", ".join(str(channel) for channel in strong_rgb),
        f"{prefix}_soft": _rgb_to_hex(soft_rgb),
        f"{prefix}_soft_2": _rgb_to_hex(soft_2_rgb),
        f"{prefix}_light": _rgb_to_hex(light_rgb),
        f"{prefix}_light_2": _rgb_to_hex(light_2_rgb),
    }


def _get_palette_translation(copy: dict[str, str], translation_code: str) -> str:
    return (
        copy.get(translation_code)
        or copy.get(DEFAULT_LANGUAGE.split("-")[0])
        or next(iter(copy.values()))
    )


def _get_palette_definition(palette_key: str | None) -> tuple[str, dict[str, Any]]:
    normalized_key = normalize_palette_key(palette_key, default=DEFAULT_PALETTE_KEY) or DEFAULT_PALETTE_KEY
    return normalized_key, BRAND_PALETTE_DEFINITIONS[normalized_key]


def _resolve_palette_from_primary_color(primary_color: str | None) -> str:
    if not is_valid_hex_color(primary_color):
        return DEFAULT_PALETTE_KEY

    normalized = normalize_hex_color(primary_color)

    for palette_key, palette_definition in BRAND_PALETTE_DEFINITIONS.items():
        if normalize_hex_color(palette_definition["colors"]["primary"]) == normalized:
            return palette_key

    source_rgb = _hex_to_rgb(normalized)
    return min(
        BRAND_PALETTE_DEFINITIONS,
        key=lambda palette_key: sum(
            (channel - target_channel) ** 2
            for channel, target_channel in zip(
                source_rgb,
                _hex_to_rgb(BRAND_PALETTE_DEFINITIONS[palette_key]["colors"]["primary"]),
            )
        ),
    )


def _resolve_palette_key(stored_preferences: dict[str, Any]) -> str:
    stored_palette_key = normalize_palette_key(stored_preferences.get("palette_key"), default=None)
    if stored_palette_key:
        return stored_palette_key

    return _resolve_palette_from_primary_color(stored_preferences.get("primary_color"))


def build_brand_palette(palette_key: str | None, translation_code: str = "pt") -> dict[str, Any]:
    normalized_key, definition = _get_palette_definition(palette_key)
    colors = {
        color_role: normalize_hex_color(definition["colors"][color_role])
        for color_role in PALETTE_COLOR_ROLES
    }

    palette: dict[str, Any] = {
        "key": normalized_key,
        "label": _get_palette_translation(definition["label"], translation_code),
        "description": _get_palette_translation(definition["description"], translation_code),
        "colors": colors,
    }
    css_variables: dict[str, str] = {}

    for color_role in PALETTE_COLOR_ROLES:
        color_family = _build_color_family(color_role, colors[color_role])
        palette.update(color_family)
        for variable_name, variable_value in color_family.items():
            css_variables[f"--mola-pro-{variable_name.replace('_', '-')}"] = variable_value

    palette["css_variables"] = css_variables
    return palette


def get_available_palettes(translation_code: str) -> list[dict[str, Any]]:
    return [
        build_brand_palette(palette_key, translation_code=translation_code)
        for palette_key in BRAND_PALETTE_DEFINITIONS
    ]


def _delete_logo(logo_path: str | None) -> None:
    if logo_path and default_storage.exists(logo_path):
        default_storage.delete(logo_path)


def _delete_favicon(favicon_path: str | None) -> None:
    if favicon_path and default_storage.exists(favicon_path):
        default_storage.delete(favicon_path)


def load_brand_preferences() -> dict[str, Any]:
    stored_preferences = _read_preferences()
    language = normalize_language_code(
        stored_preferences.get("language"),
        default=DEFAULT_LANGUAGE,
    ) or DEFAULT_LANGUAGE
    language_definition = get_language_definition(language)
    translation_code = language_definition["translation_code"]
    palette_key = _resolve_palette_key(stored_preferences)
    palette = build_brand_palette(palette_key, translation_code=translation_code)

    logo_path = stored_preferences.get("logo_path") or None
    if logo_path and not default_storage.exists(logo_path):
        logo_path = None

    favicon_path = stored_preferences.get("favicon_path") or None
    if favicon_path and not default_storage.exists(favicon_path):
        favicon_path = None

    default_logo_url = static("assets/img/logo-ct-dark.png")
    default_favicon_url = static("assets/img/favicon.png")
    logo_url = (
        f"{settings.MEDIA_URL.rstrip('/')}/{logo_path.lstrip('/')}"
        if logo_path
        else default_logo_url
    )
    favicon_url = (
        f"{settings.MEDIA_URL.rstrip('/')}/{favicon_path.lstrip('/')}"
        if favicon_path
        else default_favicon_url
    )

    return {
        "available_languages": get_available_languages(),
        "available_palettes": get_available_palettes(translation_code),
        "brand_name": DEFAULT_BRAND_NAME,
        "datatables_language_url": language_definition["datatables_language_url"],
        "default_favicon_url": default_favicon_url,
        "default_logo_url": default_logo_url,
        "favicon_path": favicon_path,
        "favicon_url": favicon_url,
        "has_custom_favicon": bool(favicon_path),
        "has_custom_logo": bool(logo_path),
        "language": language,
        "language_label": language_definition["label"],
        "logo_path": logo_path,
        "logo_url": logo_url,
        "palette": palette,
        "palette_key": palette["key"],
        "primary_color": palette["primary"],
        "translation_language": translation_code,
    }


def save_brand_preferences(
    *,
    palette_key: str | None = None,
    primary_color: str | None = None,
    language: str | None = None,
    logo_file=None,
    remove_logo: bool = False,
    favicon_file=None,
    remove_favicon: bool = False,
) -> dict[str, Any]:
    stored_preferences = _read_preferences()
    current_logo_path = stored_preferences.get("logo_path") or None
    current_favicon_path = stored_preferences.get("favicon_path") or None
    submitted_palette_key = (palette_key or "").strip()
    submitted_primary_color = (primary_color or "").strip()
    submitted_language = (language or "").strip()

    if submitted_palette_key and not is_valid_palette_key(submitted_palette_key):
        raise ValueError(_("Paleta inválida. Escolha uma das opções disponíveis."))

    if submitted_primary_color and not is_valid_hex_color(submitted_primary_color):
        raise ValueError(_("Cor primária inválida. Use um valor hexadecimal no formato #RRGGBB."))

    if submitted_language and normalize_language_code(submitted_language, default=None) is None:
        raise ValueError(_("Idioma inválido. Escolha Português (Moçambique) ou English."))

    if submitted_palette_key:
        normalized_palette_key = normalize_palette_key(submitted_palette_key, default=None) or DEFAULT_PALETTE_KEY
    elif submitted_primary_color:
        normalized_palette_key = _resolve_palette_from_primary_color(submitted_primary_color)
    else:
        normalized_palette_key = _resolve_palette_key(stored_preferences)

    primary_color_from_palette = BRAND_PALETTE_DEFINITIONS[normalized_palette_key]["colors"]["primary"]
    stored_preferences["palette_key"] = normalized_palette_key
    stored_preferences["primary_color"] = normalize_hex_color(
        primary_color_from_palette,
        default=stored_preferences.get("primary_color", DEFAULT_PRIMARY_COLOR),
    )
    stored_preferences["language"] = normalize_language_code(
        language,
        default=stored_preferences.get("language", DEFAULT_LANGUAGE),
    )

    if remove_logo:
        _delete_logo(current_logo_path)
        current_logo_path = None
        stored_preferences["logo_path"] = None

    if remove_favicon:
        _delete_favicon(current_favicon_path)
        current_favicon_path = None
        stored_preferences["favicon_path"] = None

    if logo_file:
        extension = Path(logo_file.name).suffix.lower()
        if extension not in ALLOWED_LOGO_EXTENSIONS:
            raise ValueError(_("Formato de logotipo inválido. Use PNG, JPG, JPEG, SVG ou WEBP."))

        target_logo_path = f"branding/site-logo{extension}"
        if current_logo_path and current_logo_path != target_logo_path:
            _delete_logo(current_logo_path)
        if default_storage.exists(target_logo_path):
            default_storage.delete(target_logo_path)

        stored_preferences["logo_path"] = default_storage.save(target_logo_path, logo_file)

    if favicon_file:
        extension = Path(favicon_file.name).suffix.lower()
        if extension not in ALLOWED_FAVICON_EXTENSIONS:
            raise ValueError(_("Formato de favicon inválido. Use PNG, JPG, JPEG, SVG, WEBP ou ICO."))

        target_favicon_path = f"branding/site-favicon{extension}"
        if current_favicon_path and current_favicon_path != target_favicon_path:
            _delete_favicon(current_favicon_path)
        if default_storage.exists(target_favicon_path):
            default_storage.delete(target_favicon_path)

        stored_preferences["favicon_path"] = default_storage.save(target_favicon_path, favicon_file)

    _write_preferences(stored_preferences)
    return load_brand_preferences()
