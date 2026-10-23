"""Local catalog of translators, OCR models and target languages (no network)."""

from typing import Any

from PySide6.QtCore import QObject, Signal
from modules.utils.language_utils import language_codes

_SCHEMA_VERSION = 1


def _fallback_rendering(language: str) -> dict[str, bool | str]:
    return {
        "direction": "rtl" if language in {"Arabic", "Hebrew", "Persian"} else "ltr",
        "no_space": language in {"Japanese", "Simplified Chinese", "Traditional Chinese", "Thai"},
        "vertical": language in {"Japanese", "Simplified Chinese", "Traditional Chinese"},
    }


class ClientCatalog(QObject):
    """Provides a bundled fallback, persisted cache, and non-blocking refresh."""

    updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    @staticmethod
    def fallback() -> dict[str, Any]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "translators": [
                {"id": "Gemini-3.1-Flash-Lite", "label": "Gemini-3.1-Flash-Lite", "credits": 0},
                {"id": "Gemini-2.5-Flash-Lite", "label": "Gemini-2.5-Flash-Lite", "credits": 0},
                {"id": "Gemini-2.5-Pro", "label": "Gemini-2.5-Pro", "credits": 0},
            ],
            "ocr_models": [
                {"id": "Default", "label": "Default", "credits": 0},
            ],
            "image_context_credits": 1,
            "target_languages": [
                {"value": value, "label": label, "code": language_codes[value], "rendering": _fallback_rendering(value)} for value, label in [
                    ("English", "English"), ("Korean", "한국어"), ("Japanese", "日本語"),
                    ("French", "Français"), ("Simplified Chinese", "简体中文"),
                    ("Traditional Chinese", "繁體中文"), ("Russian", "Русский"), ("German", "Deutsch"),
                    ("Dutch", "Nederlands"), ("Spanish", "Español"), ("Italian", "Italiano"),
                    ("Turkish", "Türkçe"), ("Polish", "Polski"), ("Portuguese", "Português"),
                    ("Brazilian Portuguese", "Português (Brasil)"), ("Thai", "ไทย"), ("Vietnamese", "Tiếng Việt"),
                    ("Hungarian", "Magyar"), ("Indonesian", "Bahasa Indonesia"), ("Finnish", "Suomi"),
                    ("Arabic", "العربية"), ("Hebrew", "עברית"), ("Czech", "Čeština"),
                    ("Croatian", "Hrvatski"), ("Persian", "فارسی"), ("Romanian", "Română"), ("Mongolian", "Монгол"),
                ]
            ],
        }

    def load(self) -> dict[str, Any]:
        return self.fallback()

    def refresh_async(self) -> None:
        """Bulle works fully offline: nothing is fetched from any server."""
        return None

    @staticmethod
    def _is_valid(catalog: Any) -> bool:
        return (
            isinstance(catalog, dict)
            and catalog.get("schema_version") == _SCHEMA_VERSION
            and isinstance(catalog.get("translators"), list)
            and isinstance(catalog.get("ocr_models"), list)
            and isinstance(catalog.get("image_context_credits"), int)
            and isinstance(catalog.get("target_languages"), list)
            and all(isinstance(item, dict) and isinstance(item.get("value"), str) and isinstance(item.get("label"), str)
                    and isinstance(item.get("code"), str)
                    and (
                        "rendering" not in item or (
                            isinstance(item["rendering"], dict)
                            and item["rendering"].get("direction") in {"ltr", "rtl"}
                            and isinstance(item["rendering"].get("no_space"), bool)
                            and isinstance(item["rendering"].get("vertical"), bool)
                        )
                    )
                    for item in catalog.get("target_languages", []))
        )
