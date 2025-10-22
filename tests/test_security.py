from app.bot.utils.security import (
    SENSITIVE_PLACEHOLDER,
    analyze_user_message,
    sanitize_display_name,
)


def test_invite_link_produces_high_risk() -> None:
    result = analyze_user_message(
        full_name="Ivan Ivanov",
        username="@ivan",
        message_text="Смотрите https://t.me/+secret",
    )
    assert result.should_block
    assert any("t.me/+" in reason or "t.me" in reason for reason in result.high)


def test_service_keyword_in_full_name_blocks() -> None:
    result = analyze_user_message(
        full_name="Telegram Support",
        username="@support",
        message_text="Привет",
    )
    assert result.should_block
    assert any("telegram" in reason for reason in result.high)


def test_generic_url_does_not_block_single_medium() -> None:
    result = analyze_user_message(
        full_name="Alice Example",
        username="@alice",
        message_text="Проверьте https://example.com",
    )
    assert not result.triggered
    assert not result.should_block


def test_display_name_with_at_symbol_counts_as_medium() -> None:
    result = analyze_user_message(
        full_name="@Friendly User",
        username="@friendly",
        message_text="Здравствуйте",
    )
    assert result.triggered
    assert not result.should_block
    assert any("символ @ в имени" in reason for reason in result.medium)


def test_sanitize_display_name_masks_sensitive_tokens() -> None:
    original = "t.me/+42777 Telegram-Support @User"
    sanitized = sanitize_display_name(original, placeholder="User 1")
    assert "t.me" not in sanitized.lower()
    assert "telegram" not in sanitized.lower()
    assert "@" not in sanitized
    assert sanitized != SENSITIVE_PLACEHOLDER


def test_sanitize_display_name_returns_placeholder_when_empty() -> None:
    sanitized = sanitize_display_name("t.me/+aaa", placeholder="User 99")
    assert sanitized == "User 99"
