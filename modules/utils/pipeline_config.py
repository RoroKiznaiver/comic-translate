from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from typing import TYPE_CHECKING
from modules.inpainting.lama import LaMa
from modules.inpainting.mi_gan import MIGAN
from modules.inpainting.aot import AOT
from modules.inpainting.schema import Config
from app.ui.messages import Messages
from app.ui.settings.settings_page import SettingsPage

if TYPE_CHECKING:
    from controller import ComicTranslate

inpaint_map = {
    "LaMa": LaMa,
    "MI-GAN": MIGAN,
    "AOT": AOT,
}


def get_inpainter_backend(inpainter_key: str) -> str:
    inpainter_cls = inpaint_map[inpainter_key]
    return getattr(inpainter_cls, "preferred_backend", "onnx")

def get_config(settings_page: SettingsPage):
    strategy_settings = settings_page.get_hd_strategy_settings()
    if strategy_settings['strategy'] == settings_page.ui.tr("Resize"):
        config = Config(hd_strategy="Resize", hd_strategy_resize_limit = strategy_settings['resize_limit'])
    elif strategy_settings['strategy'] == settings_page.ui.tr("Crop"):
        config = Config(hd_strategy="Crop", hd_strategy_crop_margin = strategy_settings['crop_margin'],
                        hd_strategy_crop_trigger_size = strategy_settings['crop_trigger_size'])
    else:
        config = Config(hd_strategy="Original")

    return config

def validate_ocr(main: ComicTranslate):
    """Ensure a text recognition model is selected."""
    settings_page = main.settings_page
    tr = settings_page.ui.tr
    settings = settings_page.get_all_settings()
    credentials = settings.get('credentials', {})
    ocr_tool = settings['tools']['ocr']

    if not ocr_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Text Recognition model"))
        return False
    
    return True


def validate_translator(main: ComicTranslate, target_lang: str):
    """Ensure a translator is selected and its API key is filled in."""
    settings_page = main.settings_page
    tr = settings_page.ui.tr
    settings = settings_page.get_all_settings()
    credentials = settings.get('credentials', {})
    translator_tool = settings['tools']['translator']

    if not translator_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Translator"))
        return False

    # Credential checks
    if "Custom" in translator_tool:
        # Custom requires api_key, api_url, and model to be configured LOCALLY
        service = tr('Custom')
        creds = credentials.get(service, {})
        # Check if all required fields are present and non-empty
        if not all([creds.get('api_key'), creds.get('api_url'), creds.get('model')]):
            Messages.show_custom_not_configured_error(main)
            return False
        return True

    if "Gemini" in translator_tool:
        gemini = credentials.get(tr('Google Gemini'), {})
        if not (gemini.get('api_key') or '').strip():
            Messages.show_missing_api_key_error(main, "Google Gemini")
            return False

    return True

_PREFERRED_FONTS = ["Comic Neue", "Bangers", "Comic Sans MS", "Segoe UI", "Arial"]


def ensure_default_font(main: ComicTranslate) -> bool:
    """Pick a font automatically when none is selected. True if one is set."""
    import os
    from PySide6.QtGui import QFont, QFontDatabase

    if main.render_settings().font_family:
        return True

    # Fonts dropped into resources/fonts are available without importing them.
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "fonts")
    if os.path.isdir(fonts_dir):
        for name in sorted(os.listdir(fonts_dir)):
            if name.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, name))

    available = {family.casefold(): family for family in QFontDatabase.families()}
    for wanted in _PREFERRED_FONTS:
        family = available.get(wanted.casefold())
        if not family:
            continue
        main.font_dropdown.setCurrentFont(QFont(family))
        if main.font_dropdown.currentText() != family:
            main.font_dropdown.setCurrentText(family)
        if main.render_settings().font_family:
            return True
    return False


def font_selected(main: ComicTranslate):
    if ensure_default_font(main):
        return True
    Messages.select_font_error(main)
    return False

def validate_settings(main: ComicTranslate, target_lang: str):
    if not validate_ocr(main):
        return False
    if not validate_translator(main, target_lang):
        return False
    if not font_selected(main):
        return False
    
    return True
