from __future__ import annotations

import html
from typing import Iterable

from aiogram import F, Router
from aiogram.filters import Command, MagicData, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

from app.bot.manager import Manager
from app.bot.handlers.private.windows import Window
from app.bot.utils.redis import FAQStorage, FAQAttachment, FAQItem


router = Router(name="faq")
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


class FAQStates(StatesGroup):
    """FSM states for managing FAQ entries."""

    waiting_title = State()
    waiting_content = State()
    editing_title = State()
    editing_content = State()


# -------------------------- Helpers -----------------------------------------


async def _send_faq_item(manager: Manager, item: FAQItem) -> None:
    """Deliver FAQ content to the user."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ К списку FAQ", callback_data="faq:open")
    builder.button(text="🏠 Главное меню", callback_data="faq:back")
    builder.adjust(1)

    message_text = item.text or "Материалы по выбранному вопросу находятся во вложениях ниже."

    await manager.send_message(
        message_text,
        disable_web_page_preview=True,
        reply_markup=builder.as_markup(),
        replace_previous=False,
    )

    for attachment in item.attachments:
        kwargs = {
            "chat_id": manager.user.id,
            "caption": attachment.caption,
            "parse_mode": "HTML",
        }
        if attachment.caption is None:
            kwargs.pop("caption")
            kwargs.pop("parse_mode")

        if attachment.type == "photo":
            await manager.bot.send_photo(photo=attachment.file_id, **kwargs)
        elif attachment.type == "video":
            await manager.bot.send_video(video=attachment.file_id, **kwargs)
        elif attachment.type == "document":
            await manager.bot.send_document(document=attachment.file_id, **kwargs)
        elif attachment.type == "animation":
            await manager.bot.send_animation(animation=attachment.file_id, **kwargs)
        elif attachment.type == "audio":
            await manager.bot.send_audio(audio=attachment.file_id, **kwargs)
        elif attachment.type == "voice":
            await manager.bot.send_voice(voice=attachment.file_id, **kwargs)
        elif attachment.type == "video_note":
            kwargs.pop("caption", None)
            kwargs.pop("parse_mode", None)
            await manager.bot.send_video_note(video_note=attachment.file_id, **kwargs)


async def _show_user_faq_list(manager: Manager, faq: FAQStorage) -> None:
    """Render FAQ list to the user."""
    items = await faq.list_items()
    if not items:
        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Главное меню", callback_data="faq:back")
        builder.adjust(1)
        await manager.send_message(
            "Список часто задаваемых вопросов пока пуст.",
            reply_markup=builder.as_markup(),
            replace_previous=False,
        )
        return

    builder = InlineKeyboardBuilder()
    for item in items:
        builder.button(text=item.title, callback_data=f"faq:item:{item.id}")
    builder.button(text="⬅️ Назад", callback_data="faq:back")
    builder.adjust(1)

    await manager.send_message(
        "Выберите вопрос из списка:",
        reply_markup=builder.as_markup(),
        replace_previous=False,
    )


def _collect_attachments(message: Message) -> tuple[str | None, list[FAQAttachment]]:
    """Extract text and attachments from admin message."""
    text = message.text or None
    attachments: list[FAQAttachment] = []

    if message.media_group_id:
        raise ValueError("albums_not_supported")

    if message.photo:
        file_id = message.photo[-1].file_id
        attachments.append(
            FAQAttachment(type="photo", file_id=file_id, caption=message.caption or None)
        )
        if message.caption:
            text = None
    elif message.video:
        attachments.append(
            FAQAttachment(type="video", file_id=message.video.file_id, caption=message.caption or None)
        )
        if message.caption:
            text = None
    elif message.document:
        attachments.append(
            FAQAttachment(type="document", file_id=message.document.file_id, caption=message.caption or None)
        )
        if message.caption:
            text = None
    elif message.animation:
        attachments.append(
            FAQAttachment(type="animation", file_id=message.animation.file_id, caption=message.caption or None)
        )
        if message.caption:
            text = None
    elif message.audio:
        attachments.append(
            FAQAttachment(type="audio", file_id=message.audio.file_id, caption=message.caption or None)
        )
        if message.caption:
            text = None
    elif message.voice:
        attachments.append(
            FAQAttachment(type="voice", file_id=message.voice.file_id, caption=None)
        )
    elif message.video_note:
        attachments.append(
            FAQAttachment(type="video_note", file_id=message.video_note.file_id, caption=None)
        )

    return text, attachments


def _render_admin_faq_overview(items: Iterable[FAQItem]) -> tuple[str, InlineKeyboardBuilder]:
    """Compose admin overview message and markup."""
    items = list(items)
    builder = InlineKeyboardBuilder()
    lines = ["<b>Часто задаваемые вопросы</b>"]
    if not items:
        lines.append("Список пуст. Добавьте новый вопрос, чтобы показать его пользователям.")
    else:
        lines.append("Выберите элемент для редактирования или добавьте новый вопрос.")
        for idx, item in enumerate(items, start=1):
            builder.button(text=f"{idx}. {item.title}", callback_data=f"faq:manage:{item.id}")
            lines.append(f"{idx}. {hbold(html.escape(item.title))}")
    builder.button(text="➕ Добавить вопрос", callback_data="faq:add")
    builder.button(text="⬅️ Назад", callback_data="admin:menu")
    builder.adjust(1)
    return "\n".join(lines), builder


async def _show_admin_faq_overview(manager: Manager, faq: FAQStorage) -> None:
    """Show admin menu with FAQ entries."""
    items = await faq.list_items()
    text, builder = _render_admin_faq_overview(items)
    await manager.state.set_state(None)
    await manager.send_message(text, reply_markup=builder.as_markup(), replace_previous=False)


async def _show_admin_item_menu(manager: Manager, item: FAQItem) -> None:
    """Show actions for a single FAQ entry."""
    await manager.state.update_data(faq_item_id=item.id)
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Переименовать", callback_data=f"faq:rename:{item.id}")
    builder.button(text="📝 Обновить ответ", callback_data=f"faq:content:{item.id}")
    builder.button(text="🗑 Удалить", callback_data=f"faq:delete:{item.id}")
    builder.button(text="⬅️ Назад", callback_data="faq:admin_back")
    builder.adjust(1)

    preview_lines = [
        f"<b>{html.escape(item.title)}</b>",
        "",
    ]
    if item.text:
        preview_lines.append(html.escape(item.text))
    else:
        preview_lines.append("<i>Текст отсутствует</i>")
    if item.attachments:
        preview_lines.append("")
        preview_lines.append(f"Вложения: {len(item.attachments)}")

    await manager.send_message("\n".join(preview_lines), reply_markup=builder.as_markup(), replace_previous=False)


# -------------------------- User handlers -----------------------------------


@router.callback_query(F.data == "faq:open")
async def open_user_faq(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    await _show_user_faq_list(manager, faq)
    await call.answer()


@router.callback_query(F.data == "faq:back")
async def faq_back_to_menu(call: CallbackQuery, manager: Manager) -> None:
    await Window.main_menu(manager)
    await call.answer()


@router.callback_query(F.data.startswith("faq:item:"))
async def show_faq_item(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    item_id = call.data.split(":", maxsplit=2)[-1]
    item = await faq.get_item(item_id)
    if item is None:
        await call.answer("Этот вопрос больше не доступен.", show_alert=True)
        return

    await _send_faq_item(manager, item)
    await call.answer()


# -------------------------- Admin handlers ----------------------------------


@router.message(Command("faq"), MagicData(F.event_from_user.id == F.config.bot.DEV_ID))  # type: ignore[attr-defined]
async def admin_command_faq(message: Message, manager: Manager, faq: FAQStorage) -> None:
    await _show_admin_faq_overview(manager, faq)
    await manager.delete_message(message)


@router.callback_query(
    F.data == "admin:faq",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_open_faq(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    await _show_admin_faq_overview(manager, faq)
    await call.answer()


@router.callback_query(
    F.data == "faq:add",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_add_faq(call: CallbackQuery, manager: Manager) -> None:
    await manager.state.set_state(FAQStates.waiting_title)
    await manager.state.update_data(faq_item_id=None)
    await manager.send_message("Введите заголовок для новой кнопки FAQ.", replace_previous=False)
    await call.answer()


@router.message(StateFilter(FAQStates.waiting_title))
async def admin_receive_title(message: Message, manager: Manager) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Заголовок не может быть пустым. Попробуйте ещё раз.")
        return

    await manager.state.update_data(faq_title=title)
    await manager.state.set_state(FAQStates.waiting_content)
    await manager.send_message(
        "Отправьте ответ одним сообщением. Можно приложить фото, видео или документ с подписью."
        ,
        replace_previous=False
    )
    await manager.delete_message(message)


@router.message(StateFilter(FAQStates.waiting_content))
async def admin_receive_content(message: Message, manager: Manager, faq: FAQStorage) -> None:
    try:
        text, attachments = _collect_attachments(message)
    except ValueError:
        await message.answer("Медиа-альбомы пока не поддерживаются. Отправьте ответ одним сообщением.")
        return

    if text is None and not attachments:
        await message.answer("Ответ должен содержать текст или вложение. Попробуйте ещё раз.")
        return

    state = await manager.state.get_data()
    title = state.get("faq_title")
    if not title:
        await manager.state.set_state(None)
        await message.answer("Не удалось определить заголовок. Начните добавление заново.")
        return

    await faq.add_item(title=title, text=text, attachments=attachments)
    await manager.state.set_state(None)
    await manager.state.update_data(faq_title=None)
    await manager.delete_message(message)
    await _show_admin_faq_overview(manager, faq)


@router.callback_query(
    F.data.startswith("faq:manage:"),
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_manage_item(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    item_id = call.data.split(":", maxsplit=2)[-1]
    item = await faq.get_item(item_id)
    if item is None:
        await call.answer("FAQ элемент не найден.", show_alert=True)
        return

    await manager.state.update_data(faq_item_id=item_id)
    await _show_admin_item_menu(manager, item)
    await call.answer()


@router.callback_query(
    F.data.startswith("faq:rename:"),
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_start_rename(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    item_id = call.data.split(":", maxsplit=2)[-1]
    item = await faq.get_item(item_id)
    if item is None:
        await call.answer("FAQ элемент не найден.", show_alert=True)
        return

    await manager.state.set_state(FAQStates.editing_title)
    await manager.state.update_data(faq_item_id=item_id)
    await manager.send_message(
        f"Текущий заголовок: <b>{html.escape(item.title)}</b>\nВведите новый заголовок.",
        replace_previous=False,
    )
    await call.answer()


@router.message(StateFilter(FAQStates.editing_title))
async def admin_rename_item(message: Message, manager: Manager, faq: FAQStorage) -> None:
    new_title = (message.text or "").strip()
    if not new_title:
        await message.answer("Заголовок не может быть пустым. Попробуйте снова.")
        return

    state = await manager.state.get_data()
    item_id = state.get("faq_item_id")
    if not item_id:
        await manager.state.set_state(None)
        await message.answer("Не удалось определить элемент FAQ. Начните заново.")
        return

    # state key stored as faq_item_id
    item_id = state.get("faq_item_id")
    if not item_id:
        await manager.state.set_state(None)
        await message.answer("Не удалось определить элемент FAQ. Начните заново.")
        return

    updated = await faq.rename_item(item_id, new_title)
    if updated is None:
        await manager.state.set_state(None)
        await message.answer("Элемент уже удалён.")
        return

    await manager.state.set_state(None)
    await manager.delete_message(message)
    await _show_admin_item_menu(manager, updated)


@router.callback_query(
    F.data.startswith("faq:content:"),
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_start_update_content(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    item_id = call.data.split(":", maxsplit=2)[-1]
    item = await faq.get_item(item_id)
    if item is None:
        await call.answer("FAQ элемент не найден.", show_alert=True)
        return

    await manager.state.set_state(FAQStates.editing_content)
    await manager.state.update_data(faq_item_id=item_id)
    await manager.send_message(
        "Отправьте новое содержимое ответа одним сообщением. Можно приложить медиафайл."
        ,
        replace_previous=False
    )
    await call.answer()


@router.message(StateFilter(FAQStates.editing_content))
async def admin_update_content(message: Message, manager: Manager, faq: FAQStorage) -> None:
    try:
        text, attachments = _collect_attachments(message)
    except ValueError:
        await message.answer("Медиа-альбомы пока не поддерживаются. Отправьте ответ одним сообщением.")
        return

    if text is None and not attachments:
        await message.answer("Ответ должен содержать текст или вложение. Попробуйте ещё раз.")
        return

    state = await manager.state.get_data()
    item_id = state.get("faq_item_id")
    if not item_id:
        await manager.state.set_state(None)
        await message.answer("Не удалось определить элемент FAQ. Начните заново.")
        return

    updated = await faq.update_content(item_id, text=text, attachments=attachments)
    if updated is None:
        await manager.state.set_state(None)
        await message.answer("Элемент уже удалён.")
        return

    await manager.state.set_state(None)
    await manager.delete_message(message)
    await _show_admin_item_menu(manager, updated)


@router.callback_query(
    F.data == "faq:admin_back",
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_back_to_list(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    await _show_admin_faq_overview(manager, faq)
    await call.answer()


@router.callback_query(
    F.data.startswith("faq:delete:"),
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore[attr-defined]
)
async def admin_delete_item(call: CallbackQuery, manager: Manager, faq: FAQStorage) -> None:
    item_id = call.data.split(":", maxsplit=2)[-1]
    await faq.delete_item(item_id)
    await manager.state.set_state(None)
    await _show_admin_faq_overview(manager, faq)
    await call.answer("Удалено")
