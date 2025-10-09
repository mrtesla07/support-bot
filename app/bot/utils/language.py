from __future__ import annotations

from app.bot.utils.texts import SUPPORTED_LANGUAGES


def resolve_language_code(value: str | None) -> str:
    if value in SUPPORTED_LANGUAGES:
        return value
    return next(iter(SUPPORTED_LANGUAGES.keys()))
