import os

import numpy as np

from ..utils.paths import get_user_data_dir
from ..utils.textblock import TextBlock
from ..utils.translator_utils import has_translatable_content
from .base import LLMTranslation
from .factory import TranslationFactory
from .memory import TranslationMemory, page_key

_memory = None


def get_translation_memory() -> TranslationMemory:
    global _memory
    if _memory is None:
        _memory = TranslationMemory(os.path.join(get_user_data_dir(), "translation_memory.sqlite"))
    return _memory


def memory_enabled() -> bool:
    try:
        from PySide6.QtCore import QSettings
        return QSettings("ComicLabs", "ComicTranslate").value("memory/enabled", True, type=bool)
    except Exception:
        return True


class Translator:
    """
    Main translator class that orchestrates the translation process.
    
    Supports multiple translation engines including:
    - Traditional translators (e.g Google, Microsoft, DeepL, Yandex)
    - LLM-based translators (e.g GPT, Claude, Gemini, Deepseek, Custom)
    """
    
    def __init__(self, main_page, source_lang: str = "", target_lang: str = ""):
        """
        Initialize translator with settings and languages.
        
        Args:
            main_page: Main application page with settings
            source_lang: Source language name (localized)
            target_lang: Target language name (localized)
        """
        self.main_page = main_page
        self.settings = main_page.settings_page
        
        self.translator_key = self._get_translator_key(self.settings.get_tool_selection('translator'))
        
        self.source_lang = source_lang
        self.source_lang_en = self._get_english_lang(main_page, self.source_lang)
        self.target_lang = target_lang
        self.target_lang_en = self._get_english_lang(main_page, self.target_lang)
        
        # Create appropriate engine using factory
        self.engine = TranslationFactory.create_engine(
            self.settings,
            self.source_lang_en,
            self.target_lang_en,
            self.translator_key
        )
        
        # Track engine type for method dispatching
        self.is_llm_engine = isinstance(self.engine, LLMTranslation)
    
    def _get_translator_key(self, localized_translator: str) -> str:
        """
        Map localized translator names to standard keys.
        
        Args:
            localized_translator: Translator name in UI language
            
        Returns:
            Standard translator key
        """
        translator_map = {
            self.settings.ui.tr("Custom"): "Custom",
            self.settings.ui.tr("Deepseek"): "Deepseek",
            self.settings.ui.tr("GPT-4.1"): "GPT-4.1",
            self.settings.ui.tr("GPT-4.1-mini"): "GPT-4.1-mini",
            self.settings.ui.tr("Claude-4.6-Sonnet"): "Claude-4.6-Sonnet",
            self.settings.ui.tr("Claude-4.5-Haiku"): "Claude-4.5-Haiku",
            self.settings.ui.tr("Gemini-3.1-Flash-Lite"): "Gemini-3.1-Flash-Lite",
            self.settings.ui.tr("Gemini-2.5-Pro"): "Gemini-2.5-Pro",
            self.settings.ui.tr("Microsoft Translator"): "Microsoft Translator",
            self.settings.ui.tr("DeepL"): "DeepL",
            self.settings.ui.tr("Yandex"): "Yandex"
        }
        return translator_map.get(localized_translator, localized_translator)
    
    def _get_english_lang(self, main_page, translated_lang: str) -> str:
        """
        Get English language name from localized language name.
        
        Args:
            main_page: Main application page with language mapping
            translated_lang: Language name in UI language
            
        Returns:
            Language name in English
        """
        return main_page.lang_mapping.get(translated_lang, translated_lang)
    
    def translate(self, blk_list: list[TextBlock], image: np.ndarray = None, extra_context: str = "") -> list[TextBlock]:
        """
        Translate text in text blocks using the configured translation engine.
        
        Args:
            blk_list: List of TextBlock objects to translate
            image: Image as numpy array (for context in LLM translators)
            extra_context: Additional context information for translation
            
        Returns:
            List of updated TextBlock objects with translations
        """
        translatable_blocks = []
        for block in blk_list:
            if has_translatable_content(getattr(block, "text", "")):
                translatable_blocks.append(block)
            else:
                block.translation = ""

        if not translatable_blocks:
            return blk_list

        # Translation memory: same texts, languages, translator and context as a
        # page already translated -> reuse it, send nothing, spend no tokens.
        key = None
        memory = None
        if memory_enabled():
            try:
                memory = get_translation_memory()
                key = page_key(
                    [getattr(b, "text", "") for b in translatable_blocks],
                    self.source_lang_en, self.target_lang_en, self.translator_key, extra_context,
                )
                stored = memory.get(key, len(translatable_blocks))
                if stored is not None:
                    for block, translation in zip(translatable_blocks, stored):
                        block.translation = translation
                    return blk_list
            except Exception:
                memory = None  # the memory must never break a translation

        if self.is_llm_engine:
            # LLM translators need image and extra context
            self.engine.translate(translatable_blocks, image, extra_context)
        else:
            # Text-based translators only need the text blocks
            self.engine.translate(translatable_blocks)

        if memory is not None and key is not None:
            try:
                memory.put(key, [getattr(b, "translation", "") for b in translatable_blocks])
            except Exception:
                pass
        return blk_list
