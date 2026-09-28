import logging
import time
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TooManyRequests

logger = logging.getLogger(__name__)

_CACHE = {}
_LAST_CALL = [0.0]   # throttle: min 1 second between calls
_MIN_INTERVAL = 1.0


def _throttle():
    now = time.time()
    elapsed = now - _LAST_CALL[0]
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL[0] = time.time()


class TranslatorService:

    @classmethod
    def to_english(cls, text: str, source: str = 'auto') -> str:
        if not text or not text.strip():
            return text

        key = (source, text.strip().lower())
        if key in _CACHE:
            return _CACHE[key]

        attempts = [
            ('auto', None),
            ('sn',   1.5),
            ('zu',   3.0),
        ]

        for gsrc, wait in attempts:
            if wait:
                time.sleep(wait)
            _throttle()
            try:
                translated = GoogleTranslator(
                    source=gsrc, target='en'
                ).translate(text)
                if translated and translated.strip().lower() != text.strip().lower():
                    _CACHE[key] = translated
                    logger.info(f"[{source}/{gsrc}] '{text[:50]}' -> '{translated[:50]}'")
                    return translated
            except TooManyRequests:
                logger.warning(f"429 rate limit for source={gsrc}, retrying...")
                continue
            except Exception as e:
                logger.warning(f"Translation error ({gsrc}): {e}")
                continue

        return text