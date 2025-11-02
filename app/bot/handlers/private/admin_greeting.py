from __future__ import annotations

import html
from contextlib import suppress

from aiogram import Router, F
from aiogram.filters import Command, MagicData, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

from app.bot.manager import Manager
from app.bot.handlers.private.windows import Window
from app.bot.utils.redis import SettingsStorage
from app.bot.utils.texts import SUPPORTED_LANGUAGES, TextMessage


class GreetingStates(StatesGroup):
    """FSM states for greeting management."""

    waiting_for_text = State()


router = Router(name="admin_greeting")
router.message.filter(
    F.chat.type == "private",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
router.callback_query.filter(
    F.message.chat.type == "private",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)


def _preview_text(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) > 80:
        normalized = f"{normalized[:77]}..."
    return html.escape(normalized)


def _build_menu_markup(overrides: dict[str, str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for language, title in SUPPORTED_LANGUAGES.items():
        suffix = " (обновлено)" if language in overrides else ""
        builder.button(
            text=f"✏️ {title}{suffix}",
            callback_data=f"greet:set:{language}",
        )
    builder.button(text="⬅️ Назад", callback_data="admin:menu")
    builder.button(text="✖️ Закрыть", callback_data="greet:close")
    builder.adjust(1)
    return builder


def _build_menu_text(overrides: dict[str, str]) -> str:
    lines = ["<b>Приветственные сообщения</b>", "Выберите язык, чтобы изменить текст."]

    for language, title in SUPPORTED_LANGUAGES.items():
        default_text = TextMessage(language).get("main_menu")
        preview_source = overrides.get(language, default_text)
        status = "кастом" if language in overrides else "по умолчанию"
        lines.append(
            f"{hbold(title)} — {_preview_text(preview_source)} ({status})"
        )

    lines.append("\n<i>Доступен плейсхолдер {full_name} для имени пользователя.</i>")
    return "\n".join(lines)


def _build_edit_text(language: str, current_text: str) -> str:
    language_name = SUPPORTED_LANGUAGES.get(language, language)
    escaped_current = html.escape(current_text)
    return (
        f"{hbold(language_name)}\n\n"
        "Отправьте новый текст приветствия одним сообщением.\n"
        "Можно использовать {full_name} для подстановки имени пользователя.\n\n"
        "<b>Текущее значение:</b>\n"
        f"<code>{escaped_current}</code>"
    )


def _build_edit_markup(language: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="♻️ Сбросить", callback_data=f"greet:reset:{language}")
    builder.button(text="⬅️ Назад", callback_data="greet:back")
    builder.adjust(1)
    return builder


async def _send_menu(manager: Manager, settings: SettingsStorage) -> None:
    overrides = await settings.get_all_greetings()
    markup = _build_menu_markup(overrides).as_markup()
    text = _build_menu_text(overrides)
    await manager.state.set_state(None)
    await manager.state.update_data(greeting_language=None)
    await manager.send_message(text, reply_markup=markup, replace_previous=False)


@router.message(Command("greeting"))
async def show_menu(message: Message, manager: Manager, settings: SettingsStorage) -> None:
    await _send_menu(manager, settings)
    await manager.delete_message(message)


@router.callback_query(F.data == "admin:greeting")
async def open_from_menu(call: CallbackQuery, manager: Manager, settings: SettingsStorage) -> None:
    await _send_menu(manager, settings)
    await call.answer()


@router.callback_query(F.data.startswith("greet:set:"))
async def start_edit(call: CallbackQuery, manager: Manager, settings: SettingsStorage) -> None:
    language = call.data.split(":", maxsplit=2)[-1]
    if language not in SUPPORTED_LANGUAGES:
        await call.answer("Неизвестный язык.", show_alert=True)
        return

    overrides = await settings.get_all_greetings()
    current_text = overrides.get(language, TextMessage(language).get("main_menu"))

    await manager.state.set_state(GreetingStates.waiting_for_text)
    await manager.state.update_data(greeting_language=language)

    markup = _build_edit_markup(language).as_markup()
    await manager.send_message(
        _build_edit_text(language, current_text),
        reply_markup=markup,
        replace_previous=False,
    )
    await call.answer()


@router.callback_query(F.data == "greet:back")
async def back_to_menu(call: CallbackQuery, manager: Manager, settings: SettingsStorage) -> None:
    await _send_menu(manager, settings)
    await call.answer()


@router.callback_query(F.data.startswith("greet:reset:"))
async def reset_greeting(call: CallbackQuery, manager: Manager, settings: SettingsStorage) -> None:
    language = call.data.split(":", maxsplit=2)[-1]
    if language not in SUPPORTED_LANGUAGES:
        await call.answer("Неизвестный язык.", show_alert=True)
        return

    await settings.reset_greeting(language)
    await _send_menu(manager, settings)
    await call.answer("Сброшено")


@router.callback_query(F.data == "greet:close")
async def close_menu(call: CallbackQuery, manager: Manager) -> None:
    await manager.state.set_state(None)
    await manager.state.update_data(greeting_language=None)
    with suppress(Exception):
        await call.message.delete()
    await Window.main_menu(manager)
    await call.answer("Меню закрыто")


@router.message(StateFilter(GreetingStates.waiting_for_text))
async def save_greeting(message: Message, manager: Manager, settings: SettingsStorage) -> None:
    state_data = await manager.state.get_data()
    language = state_data.get("greeting_language")
    content = (message.text or message.caption or "").strip()

    if language not in SUPPORTED_LANGUAGES:
        await manager.state.set_state(None)
        await _send_menu(manager, settings)
        await message.answer("Не удалось определить язык. Попробуйте ещё раз.")
        return

    if not content:
        await message.answer("Пожалуйста, отправьте непустой текст.")
        return

    await settings.set_greeting(language, content)
    await manager.state.update_data(greeting_language=None)
    await _send_menu(manager, settings)
    await manager.delete_message(message)
