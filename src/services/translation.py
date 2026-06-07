import logging
from abc import ABC, abstractmethod
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

class TranslationError(Exception):
    """Base exception for translation errors."""
    pass

class TranslationProvider(ABC):
    @abstractmethod
    def translate(self, text: str, source: str, target: str) -> str:
        """Translate text from source language to target language."""
        pass

class GoogleTranslateProvider(TranslationProvider):
    def translate(self, text: str, source: str, target: str) -> str:
        try:
            translator = GoogleTranslator(source=source, target=target)
            result = translator.translate(text)
            if not result:
                raise TranslationError("Google Translate returned an empty response.")
            return result
        except Exception as e:
            logger.error(f"Error in GoogleTranslate translation: {e}")
            raise TranslationError(f"Failed to translate: {str(e)}")

class TranslationService:
    def __init__(self):
        self.provider = GoogleTranslateProvider()

    def translate_message(self, text: str) -> tuple[str, str, str]:
        """
        Detects language and translates to the opposite language (Tamil <-> English).
        Returns: (translated_text, source_lang, target_lang)
        """
        if not text or not text.strip():
            raise TranslationError("Message text is empty")

        # Simple unicode check: Tamil block ranges from U+0B80 to U+0BFF
        has_tamil = any('\u0b80' <= char <= '\u0bff' for char in text)
        
        if has_tamil:
            source = "ta"
            target = "en"
        else:
            source = "en"
            target = "ta"

        translated = self.provider.translate(text, source, target)
        return translated, source, target

translation_service = TranslationService()
