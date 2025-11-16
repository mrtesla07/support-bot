from dataclasses import dataclass
from urllib.parse import quote

from environs import Env


@dataclass
class BotConfig:
    """
    Data class representing the configuration for the bot.

    Attributes:
    - TOKEN (str): The bot token.
    - DEV_ID (int): The developer's user ID.
    - GROUP_ID (int): The group chat ID.
    - BOT_EMOJI_ID (str): The custom emoji ID for new or unanswered topics.
    - BOT_ACTIVE_EMOJI_ID (str): The custom emoji ID used when the operator has replied.
    - BOT_RESOLVED_EMOJI_ID (str): The custom emoji ID used when a ticket is resolved.
    """
    TOKEN: str
    DEV_ID: int
    GROUP_ID: int
    BOT_EMOJI_ID: str
    BOT_ACTIVE_EMOJI_ID: str
    BOT_RESOLVED_EMOJI_ID: str
    DEFAULT_LANGUAGE: str
    LANGUAGE_PROMPT_ENABLED: bool
    REMINDERS_ENABLED: bool


@dataclass
class RedisConfig:
    """
    Data class representing the configuration for Redis.

    Attributes:
    - HOST (str): The Redis host.
    - PORT (int): The Redis port.
    - DB (int): The Redis database number.
    """
    HOST: str
    PORT: int
    DB: int
    PASSWORD: str | None = None

    def dsn(self) -> str:
        """
        Generates a Redis connection DSN (Data Source Name) using the provided host, port, and database.

        :return: The generated DSN.
        """
        if self.PASSWORD:
            encoded_password = quote(self.PASSWORD, safe="")
            return f"redis://:{encoded_password}@{self.HOST}:{self.PORT}/{self.DB}"
        return f"redis://{self.HOST}:{self.PORT}/{self.DB}"


@dataclass
class Config:
    """
    Data class representing the overall configuration for the application.

    Attributes:
    - bot (BotConfig): The bot configuration.
    - redis (RedisConfig): The Redis configuration.
    - security_enabled (bool): Toggles anti-spam security filters.
    """
    bot: BotConfig
    redis: RedisConfig
    security_enabled: bool


def load_config() -> Config:
    """
    Load the configuration from environment variables and return a Config object.

    :return: The Config object with loaded configuration.
    """
    env = Env()
    env.read_env()

    return Config(
        bot=BotConfig(
            TOKEN=env.str("BOT_TOKEN"),
            DEV_ID=env.int("BOT_DEV_ID"),
            GROUP_ID=env.int("BOT_GROUP_ID"),
            BOT_EMOJI_ID=env.str("BOT_EMOJI_ID"),
            BOT_ACTIVE_EMOJI_ID=env.str("BOT_ACTIVE_EMOJI_ID"),
            BOT_RESOLVED_EMOJI_ID=env.str("BOT_RESOLVED_EMOJI_ID"),
            DEFAULT_LANGUAGE=env.str("BOT_DEFAULT_LANGUAGE", default="en"),
            LANGUAGE_PROMPT_ENABLED=env.bool("BOT_LANGUAGE_PROMPT_ENABLED", default=True),
            REMINDERS_ENABLED=env.bool("BOT_REMINDERS_ENABLED", default=True),
        ),
        redis=RedisConfig(
            HOST=env.str("REDIS_HOST"),
            PORT=env.int("REDIS_PORT"),
            DB=env.int("REDIS_DB"),
            PASSWORD=env.str("REDIS_PASSWORD", default="") or None,
        ),
        security_enabled=env.bool("SECURITY_FILTER_ENABLED", default=True),
    )
