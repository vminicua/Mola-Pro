from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.files.storage import default_storage
from django.templatetags.static import static


DEFAULT_BRAND_NAME = "Mola Pro"
DEFAULT_PRIMARY_COLOR = "#064E3B"
PREFERENCES_RELATIVE_PATH = "preferences/branding.json"
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
ALLOWED_FAVICON_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}


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


def build_brand_palette(primary_color: str) -> dict[str, str]:
    normalized = normalize_hex_color(primary_color)
    primary_rgb = _hex_to_rgb(normalized)
    brightness = sum(primary_rgb) / 3

    hover_rgb = _mix(
        primary_rgb,
        (255, 255, 255) if brightness < 110 else (0, 0, 0),
        0.12 if brightness < 110 else 0.08,
    )
    strong_rgb = _mix(primary_rgb, (0, 0, 0), 0.08 if brightness < 90 else 0.18)
    soft_rgb = _mix(primary_rgb, (255, 255, 255), 0.88)
    soft_2_rgb = _mix(primary_rgb, (255, 255, 255), 0.94)
    light_rgb = _mix(primary_rgb, (255, 255, 255), 0.55)
    light_2_rgb = _mix(primary_rgb, (255, 255, 255), 0.72)

    return {
        "primary": normalized,
        "primary_rgb": ", ".join(str(channel) for channel in primary_rgb),
        "primary_hover": _rgb_to_hex(hover_rgb),
        "primary_hover_rgb": ", ".join(str(channel) for channel in hover_rgb),
        "primary_active": normalized,
        "primary_active_rgb": ", ".join(str(channel) for channel in primary_rgb),
        "primary_strong": _rgb_to_hex(strong_rgb),
        "primary_strong_rgb": ", ".join(str(channel) for channel in strong_rgb),
        "primary_soft": _rgb_to_hex(soft_rgb),
        "primary_soft_2": _rgb_to_hex(soft_2_rgb),
        "primary_light": _rgb_to_hex(light_rgb),
        "primary_light_2": _rgb_to_hex(light_2_rgb),
    }


def _delete_logo(logo_path: str | None) -> None:
    if logo_path and default_storage.exists(logo_path):
        default_storage.delete(logo_path)


def _delete_favicon(favicon_path: str | None) -> None:
    if favicon_path and default_storage.exists(favicon_path):
        default_storage.delete(favicon_path)


def load_brand_preferences() -> dict[str, Any]:
    stored_preferences = _read_preferences()
    primary_color = normalize_hex_color(
        stored_preferences.get("primary_color"),
        default=DEFAULT_PRIMARY_COLOR,
    )

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
        "brand_name": DEFAULT_BRAND_NAME,
        "default_favicon_url": default_favicon_url,
        "default_logo_url": default_logo_url,
        "favicon_path": favicon_path,
        "favicon_url": favicon_url,
        "has_custom_favicon": bool(favicon_path),
        "has_custom_logo": bool(logo_path),
        "logo_path": logo_path,
        "logo_url": logo_url,
        "palette": build_brand_palette(primary_color),
        "primary_color": primary_color,
    }


def save_brand_preferences(
    *,
    primary_color: str | None,
    logo_file=None,
    remove_logo: bool = False,
    favicon_file=None,
    remove_favicon: bool = False,
) -> dict[str, Any]:
    stored_preferences = _read_preferences()
    current_logo_path = stored_preferences.get("logo_path") or None
    current_favicon_path = stored_preferences.get("favicon_path") or None
    submitted_primary_color = (primary_color or "").strip()

    if submitted_primary_color and not is_valid_hex_color(submitted_primary_color):
        raise ValueError("Cor primária inválida. Use um valor hexadecimal no formato #RRGGBB.")

    stored_preferences["primary_color"] = normalize_hex_color(
        primary_color,
        default=stored_preferences.get("primary_color", DEFAULT_PRIMARY_COLOR),
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
            raise ValueError("Formato de logotipo inválido. Use PNG, JPG, JPEG, SVG ou WEBP.")

        target_logo_path = f"branding/site-logo{extension}"
        if current_logo_path and current_logo_path != target_logo_path:
            _delete_logo(current_logo_path)
        if default_storage.exists(target_logo_path):
            default_storage.delete(target_logo_path)

        stored_preferences["logo_path"] = default_storage.save(target_logo_path, logo_file)

    if favicon_file:
        extension = Path(favicon_file.name).suffix.lower()
        if extension not in ALLOWED_FAVICON_EXTENSIONS:
            raise ValueError("Formato de favicon inválido. Use PNG, JPG, JPEG, SVG, WEBP ou ICO.")

        target_favicon_path = f"branding/site-favicon{extension}"
        if current_favicon_path and current_favicon_path != target_favicon_path:
            _delete_favicon(current_favicon_path)
        if default_storage.exists(target_favicon_path):
            default_storage.delete(target_favicon_path)

        stored_preferences["favicon_path"] = default_storage.save(target_favicon_path, favicon_file)

    _write_preferences(stored_preferences)
    return load_brand_preferences()
