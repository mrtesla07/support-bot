# Support Bot

[![License](https://img.shields.io/github/license/mrtesla07/support-bot)](LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Bot-grey?logo=telegram)](https://core.telegram.org/bots)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-enabled?logo=redis&color=red)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

Support Bot — телеграм-бот для поддержки пользователей. Он принимает обращения в личных сообщениях, продублирует их в форуме рабочей группы и синхронизирует состояние (тикеты, статусы, напоминания) через Redis.

## Возможности

- автоматическое создание отдельной форумной темы под каждого пользователя;
- зеркалирование сообщений и медиагрупп между приватным чатом и форуме поддержки;
- напоминания операторам о «висящих» обращениях;
- служебные команды `/resolve`, `/silent`, `/ban`, `/information`, `/newsletter`;
- антиспам-защита: фильтр инвайтов/ссылок, санитация имён, автоматический бан подозрительных профилей.

<details>
<summary><b>Админ-команды (для DEV_ID)</b></summary>

* `/newsletter` — открыть меню рассылки (требует aiogram_newsletter).
* `/greeting` — настроить приветственное сообщение (доступны плейсхолдеры `{full_name}`).
* `/closing` — настроить сообщение, которое отправляется пользователю после /resolve (поддерживает `{full_name}`).
</details>

<details>
<summary><b>Команды в форуме</b></summary>

* `/ban` — переключить блокировку пользователя (сообщения перестают пересылаться).
* `/silent` — включить бесшумный режим (ответы не доставляются пользователю).
* `/information` — вывести карточку пользователя (ID, username, статус, дата регистрации).
* `/resolve` — пометить тикет как «решён», сменить эмодзи темы и отправить пользователю финальное сообщение.
</details>

## Быстрый старт (локально)

```bash
git clone https://github.com/mrtesla07/support-bot.git
cd support-bot
cp .env.example .env
nano .env          # заполните токен бота и параметры Redis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app
```

### Запуск через Docker

```bash
docker compose up -d --build
```

## Обновление и миграции

```bash
docker compose down
git pull
docker compose up -d --build
```

- `--build` пересобирает контейнер и подтягивает свежие зависимости из `requirements.txt`.
- Redis хранит данные в отдельном volume, поэтому не очищается без `docker compose down -v`.
- При старте приложение автоматически выполняет миграции из `app/migrations` (санитация имён, обновление записей, переименование тем). Дополнительных действий не требуется.

## Переменные окружения

| Имя                    | Описание                                              |
|------------------------|--------------------------------------------------     |
| `BOT_TOKEN`            | токен, выданный [@BotFather](https://t.me/BotFather)  |
| `BOT_DEV_ID`           | Telegram ID администратора (доступ к /newsletter)     |
| `BOT_GROUP_ID`         | ID чат-форума, куда пересылаются обращения            |
| `BOT_EMOJI_ID`         | кастомное эмодзи для активных тем                     |
| `BOT_RESOLVED_EMOJI_ID`| эмодзи для решённых тикетов                           |
| `BOT_DEFAULT_LANGUAGE` | код языка по умолчанию (`en`, `ru`, и т.п.)           |
| `BOT_LANGUAGE_PROMPT_ENABLED` | `true/false`, показывать ли окно выбора языка  |
| `REDIS_HOST`           | адрес Redis                                           |
| `REDIS_PORT`           | порт Redis                                            |
| `REDIS_DB`             | номер базы Redis                                      |

Если выбор языка не нужен, задайте `BOT_DEFAULT_LANGUAGE` и отключите шаг выбора, выставив `BOT_LANGUAGE_PROMPT_ENABLED=false`. Тогда пользователь сразу открывает главное меню на выбранном языке.

## Тесты

```bash
pytest
```

## Технологии

- Python 3.12, [aiogram](https://docs.aiogram.dev) 3.x;
- Redis + APScheduler для хранения состояния и напоминаний;
- Docker Compose в качестве рекомендованного окружения.

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
