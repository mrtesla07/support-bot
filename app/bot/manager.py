import asyncio
from contextlib import suppress
from typing import Any, Dict

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ForceReply,
    User,
)
from aiogram.types.base import (
    UNSET_DISABLE_WEB_PAGE_PREVIEW,
    UNSET_PARSE_MODE,
)

from app.bot.utils.texts import TextMessage
from app.config import Config

MESSAGE_EDIT_ERRORS = [
    "message can't be edited",
    "message is not modified",
    "message to edit not found",
]
MESSAGE_DELETE_ERRORS = [
    "message can't be deleted",
    "message to delete not found",
]


class Manager:
    """
    Manager class for handling bot-related operations and messaging.
    """

    def __init__(self, emoji: str, data: Dict[str, Any], language_code: str) -> None:
        """
        Initialize the Manager instance.

        :param emoji: The emoji string.
        :param data: Additional data.
        :param language_code: The language code for localization.
        """
        self.bot: Bot = data.get("bot")
        self.state: FSMContext = data.get("state")
        self.user: User = data.get("event_from_user")

        self.config: Config = data.get("config")
        self.text_message = TextMessage(language_code)

        self.__emoji = emoji
        self.__data = data

    @property
    def middleware_data(self) -> Dict[str, Any]:
        """
        Get middleware data.

        :return: Middleware data.
        """
        return self.__data

    async def get_old_message_id(self) -> int | None:
        """
        Get the old message ID stored in the FSM context.

        :return: The old message ID if present, otherwise None.
        """
        data = await self.state.get_data()
        message_id = data.get("message_id")
        return message_id if isinstance(message_id, int) else None

    async def send_message(
            self,
            text: str,
            parse_mode: str | None = UNSET_PARSE_MODE,
            disable_web_page_preview: bool | None = UNSET_DISABLE_WEB_PAGE_PREVIEW,
            disable_notification: bool | None = None,
            reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None = None,
            *,
            replace_previous: bool = True,
    ) -> None:
        """
        Send a message using the bot.

        :param text: The text of the message.
        :param parse_mode: The parse mode of the message.
        :param disable_web_page_preview: Disable web page preview.
        :param disable_notification: Disable notification.
        :param reply_markup: The reply markup.
        :param replace_previous: Whether to delete the previous message instead of editing it.

        :return: None.
        """
        previous_message_id = await self.get_old_message_id()

        if not replace_previous and previous_message_id is not None:
            try:
                await self.bot.edit_message_text(
                    text=text,
                    chat_id=self.user.id,
                    message_id=previous_message_id,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview,
                    reply_markup=reply_markup,
                )
                await self.state.update_data(message_id=previous_message_id)
                return
            except TelegramBadRequest as ex:
                if not any(e in ex.message for e in MESSAGE_EDIT_ERRORS):
                    raise ex
                await self.delete_previous_message()

        if replace_previous:
            await self.delete_previous_message()

        message = await self.bot.send_message(
            text=text,
            chat_id=self.user.id,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )
        await self.state.update_data(message_id=message.message_id)

    @staticmethod
    def schedule_message_cleanup(message: Message, delay: float = 5.0) -> None:
        """
        Schedule deletion of a message after a given delay.

        :param message: The message that should be removed.
        :param delay: Delay in seconds before deletion.
        """
        async def _cleanup() -> None:
            await asyncio.sleep(delay)
            with suppress(TelegramBadRequest):
                await message.delete()

        asyncio.create_task(_cleanup())

    @staticmethod
    async def delete_message(message: Message) -> None:
        """
        Delete a message using the bot.

        :param message: The message to be deleted.
        """
        with suppress(TelegramBadRequest):
            await message.delete()

    async def delete_previous_message(self) -> None | Message:
        """
        Delete the previous message.

        This method attempts to delete the previous message identified by the stored message ID. If deletion is not
        possible (e.g., due to a message not found error), it attempts to edit the previous message with a placeholder
        __emoji. If editing is also not possible, it raises TelegramBadRequest with the appropriate error message.

        :return: The edited Message object or None if no previous message was found.

        :raise TelegramBadRequest: If there is an issue with deleting or editing the previous message.
        """
        message_id = await self.get_old_message_id()
        if message_id is None:
            return None

        try:
            await self.bot.delete_message(
                message_id=message_id,
                chat_id=self.user.id,
            )
        except TelegramBadRequest as ex:
            if any(e in ex.message for e in MESSAGE_DELETE_ERRORS):
                try:
                    return await self.bot.edit_message_text(
                        message_id=message_id,
                        chat_id=self.user.id,
                        text=self.__emoji,
                    )
                except TelegramBadRequest as ex:
                    if not any(e in ex.message for e in MESSAGE_EDIT_ERRORS):
                        raise ex
