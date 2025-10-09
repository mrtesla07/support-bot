from app.bot.utils.language import resolve_language_code
from app.bot.utils.texts import SUPPORTED_LANGUAGES


def test_resolve_language_code_valid_values():
    for code in SUPPORTED_LANGUAGES:
        assert resolve_language_code(code) == code


def test_resolve_language_code_fallback():
    fallback = resolve_language_code("xx")
    assert fallback in SUPPORTED_LANGUAGES
