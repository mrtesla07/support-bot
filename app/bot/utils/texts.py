from abc import ABCMeta, abstractmethod

from aiogram.utils.markdown import hbold

SUPPORTED_LANGUAGES = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}


class Text(metaclass=ABCMeta):
    """Abstract base class for handling text data in different languages."""

    def __init__(self, language_code: str) -> None:
        self.language_code = language_code if language_code in SUPPORTED_LANGUAGES else "en"

    @property
    @abstractmethod
    def data(self) -> dict:
        raise NotImplementedError

    def get(self, code: str) -> str:
        return self.data[self.language_code][code]


class TextMessage(Text):
    """Language-aware texts used by the bot."""

    @property
    def data(self) -> dict:
        return {
            "en": {
                "select_language": f"👋 <b>Hello</b>, {hbold('{full_name}')}!\n\nSelect language:",
                "change_language": "<b>Select language:</b>",
                "main_menu": "<b>Write your question</b>, and we will answer you as soon as possible:",
                "message_sent": "<b>Message sent!</b> Expect a response.",
                "faq_suggestion": (
                    "While you wait for a response, take a look at the frequently asked questions "
                    "— the answer might already be there."
                ),
                "message_edited": (
                    "<b>The message was edited only in your chat.</b> "
                    "If you want support to receive the new version, send it again."
                ),
                "source": (
                    "Source code available at "
                    "<a href=\"https://github.com/mrtesla07/support-bot\">GitHub</a>"
                ),
                "user_started_bot": (
                    f"User {hbold('{name}')} started the bot!\n\n"
                    "List of available commands:\n\n"
                    "- /ban\n"
                    "  Block or unblock the user.\n\n"
                    "- /silent\n"
                    "  Toggle silent mode. When enabled, replies are not sent to the user.\n\n"
                    "- /information\n"
                    "  Show a brief summary about the user.\n\n"
                    "- /resolve\n"
                    "  Mark the ticket as resolved and update the topic emoji.\n\n"
                    "- /resolvequiet\n"
                    "  Close the ticket without sending a message to the user."
                ),
                "user_restarted_bot": f"User {hbold('{name}')} restarted the bot!",
                "user_stopped_bot": f"User {hbold('{name}')} stopped the bot!",
                "user_blocked": "<b>User blocked!</b> Messages from the user are ignored.",
                "user_unblocked": "<b>User unblocked!</b> Messages from the user are accepted again.",
                "blocked_by_user": "<b>Message not sent!</b> The bot is blocked by the user.",
                "user_information": (
                    "<b>ID:</b>\n"
                    "- <code>{id}</code>\n"
                    "<b>Name:</b>\n"
                    "- {full_name}\n"
                    "<b>Status:</b>\n"
                    "- {state}\n"
                    "<b>Username:</b>\n"
                    "- {username}\n"
                    "<b>Blocked:</b>\n"
                    "- {is_banned}\n"
                    "<b>Registration date:</b>\n"
                    "- {created_at}"
                ),
                "message_not_sent": "<b>Message not sent!</b> An unexpected error occurred.",
                "message_sent_to_user": "<b>Message sent to the user!</b>",
                "support_panel_prompt": "Choose an action for {full_name} (status: {status}).",
                "ticket_status_open": "open",
                "ticket_status_resolved": "resolved",
                "support_panel_reply_prompt": "Reply to {full_name}. Send your message below.",
                "support_panel_reply_placeholder": "Reply to the user",
                "support_panel_reply_hint": "Write the response in this chat.",
                "support_panel_postponed": "Reminder postponed for 5 minutes.",
                "support_panel_status_changed": "Ticket status updated.",
                "auto_blocked_notice": (
                    "<b>Message blocked.</b>\n"
                    "Our safety filter detected suspicious data ({reason}).\n"
                    "Please rename your profile and remove invite links before trying again."
                ),
                "auto_blocked_alert": (
                    "<b>Automatic block triggered.</b>\n"
                    "{user}\n"
                    "Reason: {reason}"
                ),
                "silent_mode_enabled": (
                    "<b>Silent mode enabled!</b> Messages will not be forwarded to the user."
                ),
                "silent_mode_disabled": (
                    "<b>Silent mode disabled!</b> The user will receive all messages."
                ),
                "support_reminder": (
                    "<b>User {user} is waiting for a reply.</b>\nPlease check the conversation."
                ),
                "ticket_resolved": "<b>Ticket marked as resolved.</b>",
                "ticket_reopened": "<b>Ticket reopened.</b>",
                "ticket_resolved_user": (
                    "<b>Thank you for reaching out!</b>\n"
                    "Your ticket is now closed, but you can reply here if you need more help."
                ),
            },
            "ru": {
                "select_language": f"👋 <b>Привет</b>, {hbold('{full_name}')}!\n\nВыберите язык:",
                "change_language": "<b>Выберите язык:</b>",
                "main_menu": "<b>Напишите свой вопрос</b>, и мы ответим как можно быстрее:",
                "message_sent": "<b>Сообщение отправлено!</b> Ожидайте ответа.",
                "faq_suggestion": (
                    "Пока вы ждёте ответа, загляните в раздел часто задаваемых вопросов — возможно, решение уже есть."
                ),
                "message_edited": (
                    "<b>Сообщение изменено только в вашем чате.</b> "
                    "Если хотите, чтобы поддержка увидела новую версию, отправьте сообщение заново."
                ),
                "source": (
                    "Исходный код доступен на "
                    "<a href=\"https://github.com/mrtesla07/support-bot\">GitHub</a>"
                ),
                "user_started_bot": (
                    f"Пользователь {hbold('{name}')} запустил бота!\n\n"
                    "Список доступных команд:\n\n"
                    "- /ban\n"
                    "  Заблокировать или разблокировать пользователя.\n\n"
                    "- /silent\n"
                    "  Включить или выключить тихий режим. В тихом режиме ответы не отправляются пользователю.\n\n"
                    "- /information\n"
                    "  Показать краткую информацию о пользователе.\n\n"
                    "- /resolve\n"
                    "  Отметить тикет решённым и сменить эмодзи темы.\n\n"
                    "- /resolvequiet\n"
                    "  Закрыть тикет без сообщения пользователю."
                ),
                "user_restarted_bot": f"Пользователь {hbold('{name}')} перезапустил бота!",
                "user_stopped_bot": f"Пользователь {hbold('{name}')} остановил бота!",
                "user_blocked": "<b>Пользователь заблокирован!</b> Сообщения от него игнорируются.",
                "user_unblocked": "<b>Пользователь разблокирован!</b> Сообщения снова принимаются.",
                "blocked_by_user": "<b>Сообщение не отправлено!</b> Бот заблокирован пользователем.",
                "user_information": (
                    "<b>ID:</b>\n"
                    "- <code>{id}</code>\n"
                    "<b>Имя:</b>\n"
                    "- {full_name}\n"
                    "<b>Статус:</b>\n"
                    "- {state}\n"
                    "<b>Username:</b>\n"
                    "- {username}\n"
                    "<b>Заблокирован:</b>\n"
                    "- {is_banned}\n"
                    "<b>Дата регистрации:</b>\n"
                    "- {created_at}"
                ),
                "message_not_sent": "<b>Сообщение не отправлено!</b> Произошла непредвиденная ошибка.",
                "message_sent_to_user": "<b>Сообщение отправлено пользователю!</b>",
                "support_panel_prompt": "Выберите действие для {full_name} (статус: {status}).",
                "ticket_status_open": "открыт",
                "ticket_status_resolved": "решён",
                "support_panel_reply_prompt": "Ответ пользователю {full_name}. Отправьте сообщение ниже.",
                "support_panel_reply_placeholder": "Ответ пользователю",
                "support_panel_reply_hint": "Введите ответ в этом чате.",
                "support_panel_postponed": "Напоминание отложено на 5 минут.",
                "support_panel_status_changed": "Статус тикета обновлён.",
                "auto_blocked_notice": (
                    "<b>Сообщение заблокировано.</b>\n"
                    "Фильтр безопасности обнаружил подозрительные данные ({reason}).\n"
                    "Уберите ссылки и сервисные маски и попробуйте снова."
                ),
                "auto_blocked_alert": (
                    "<b>Включена авто-блокировка.</b>\n"
                    "{user}\n"
                    "Причина: {reason}"
                ),
                "silent_mode_enabled": (
                    "<b>Тихий режим включён!</b> Сообщения не будут пересылаться пользователю."
                ),
                "silent_mode_disabled": (
                    "<b>Тихий режим выключен!</b> Пользователь снова получает сообщения."
                ),
                "support_reminder": (
                    "<b>{user} ждёт ответа.</b>\nПроверьте, пожалуйста, тему."
                ),
                "ticket_resolved": "<b>Тикет отмечен как решённый.</b>",
                "ticket_reopened": "Тикет снова открыт.",
                "ticket_resolved_user": (
                    "<b>Спасибо за обращение!</b>\n"
                    "Тикет закрыт. Если помощь ещё нужна, просто ответьте в этом чате."
                ),
            },
        }
