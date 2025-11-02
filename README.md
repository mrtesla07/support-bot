# Support Bot

[![License](https://img.shields.io/github/license/mrtesla07/support-bot)](LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Bot-grey?logo=telegram)](https://core.telegram.org/bots)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-enabled?logo=redis&color=red)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

Все предложения и пожелания можете присылать сюда https://t.me/FederikoFellinni

Support Bot — телеграм-бот для поддержки пользователей. Он принимает обращения в личных сообщениях, продублирует их в форуме рабочей группы и синхронизирует состояние (тикеты, статусы, напоминания) через Redis.

## Возможности

- автоматическое создание отдельной форумной темы под каждого пользователя;
- зеркалирование сообщений и медиагрупп между приватным чатом и форуме поддержки;
- напоминания операторам о «висящих» обращениях;
- служебные команды `/resolve`, `/resolvequiet`, `/silent`, `/ban`, `/information`, `/newsletter`;
- инлайн-панель операторов в групповой теме (кнопки «Ответить», «Отложить», «Сменить статус», «Инфо»);
- встроенный раздел «Часто задаваемые вопросы» с кнопкой для пользователей и управлением контентом (текст, фото, видео, документы) через админку;
- антиспам-защита: фильтр инвайтов/ссылок, санитация имён, автоматический бан подозрительных профилей.

<details>
<summary><b>Админ-команды (для DEV_ID)</b></summary>

* `/newsletter` — открыть меню рассылки (требует aiogram_newsletter).
* `/greeting` — настроить приветственное сообщение (доступны плейсхолдеры `{full_name}`).
* `/closing` — настроить сообщение, которое отправляется пользователю после /resolve (поддерживает `{full_name}`).
* `/faq` — открыть редактор FAQ: добавление, переименование, обновление ответов с вложениями.
</details>

<details>
<summary><b>Команды в форуме</b></summary>

* `/ban` — переключить блокировку пользователя (сообщения перестают пересылаться).
* `/silent` — включить бесшумный режим (ответы не доставляются пользователю).
* `/information` — вывести карточку пользователя (ID, username, статус, дата регистрации).
* `/resolve` — пометить тикет как «решён», сменить эмодзи темы и отправить пользователю финальное сообщение.
* `/resolvequiet` — закрыть тикет без отправки финального сообщения пользователю.
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

- Redis запускается с включённым AOF и сохраняет данные в каталоге `redis/data`. После `docker compose down` состояние остаётся, пока вы не выполните `docker compose down -v`.
- Пароль для Redis берётся из переменной `REDIS_PASSWORD`; задайте в `.env` уникальное значение перед деплоем.
- Docker автоматически создаёт каталог `redis/data` и выставляет на него права. Если вы запускаете rootless Docker или сталкиваетесь с `Permission denied`, создайте каталог вручную и выдать права пользователю Redis:
  ```bash
  mkdir -p redis/data
  # Узнайте UID/GID образа: docker run --rm redis:alpine id redis
  sudo chown -R 1001:1001 redis/data  # замените на значения из предыдущей команды
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
| `REDIS_PASSWORD`       | пароль для подключения к Redis (оставьте пустым, если не нужен) |

Если выбор языка не нужен, задайте `BOT_DEFAULT_LANGUAGE` и отключите шаг выбора, выставив `BOT_LANGUAGE_PROMPT_ENABLED=false`. Тогда пользователь сразу открывает главное меню на выбранном языке.
Если напоминания в группе не нужны, установите `BOT_REMINDERS_ENABLED=false` — бот перестанет планировать сообщения о просроченных ответах.

## Тесты

```bash
pytest
```

## Документация для разработчиков

- [Руководство по разработке](docs/DEVELOPMENT.md)
- [Дорожная карта](docs/ROADMAP.md)

## Автоустановка

Для развёртывания на чистом сервере есть скрипт `scripts/s-b.sh`. Он:
- ставит Docker (Ubuntu или через официальный `get.docker.com`);
- клонирует/обновляет `support-bot` в выбранный каталог (по умолчанию `/opt/support-bot`);
- копирует `.env.example`, позволяет задать `BOT_TOKEN`, `BOT_DEV_ID`, `BOT_GROUP_ID`, `BOT_DEFAULT_LANGUAGE`, `BOT_LANGUAGE_PROMPT_ENABLED` и запускает `docker compose up -d --build`;
- поддерживает меню с операциями `up/down/logs/pull`, self-update из репозитория.

### Как использовать

```bash
curl -fsSL https://raw.githubusercontent.com/mrtesla07/support-bot/main/scripts/s-b.sh \
  | bash
```

Скрипт при старте спрашивает каталог установки (Enter — оставить `/opt/support-bot`) и автоматически копирует себя в `/usr/local/bin/s-b`, поэтому после первого запуска можно просто набрать `s-b` из любого каталога и открыть меню (установка, обновление, пересоздание `.env`, перезапуск и т.д.).

## Несколько ботов

Чтобы один сервер обслуживал несколько проектов, для каждого бота поднимайте **самостоятельный экземпляр** приложения. Действуйте последовательно.

1. **Выделите каталог под проект**
   ```bash
   /opt/support-bot-project-a
   /opt/support-bot-project-b
   ```
   Внутри каталога разместите исходники (git clone или копию репозитория).

2. **Создайте собственный `.env`**
   ```bash
   cp .env.example .env
   ```
   Задайте уникальные значения: `BOT_TOKEN`, `BOT_DEV_ID`, `BOT_GROUP_ID`, `BOT_EMOJI_ID`, `BOT_RESOLVED_EMOJI_ID`, `BOT_REMINDERS_ENABLED`, а также параметры Redis (`REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`). Минимум — используйте отдельный номер базы.

3. **Скопируйте и настройте `docker-compose.yml`**
   - переименуйте сервисы и контейнеры, чтобы имена не конфликтовали (например, `support-bot-project-a`, `support-redis-project-a`);
   - подключите отдельный том для Redis, чтобы данные не смешивались:
     ```yaml
     volumes:
       - ./redis/data-project-a:/data
     ```

4. **Запускайте и обновляйте каждый проект отдельно**
   ```bash
   docker compose up -d --build
   ```
   Команду выполняйте из каталога конкретного бота. Обновления (`git pull`, `docker compose down && docker compose up -d --build`) и просмотр логов (`docker compose logs`) тоже проводите по очереди.

5. **Делайте независимые бэкапы**
   Перед `scripts/redis_backup.py` подгружайте `.env` нужного проекта (или задавайте переменные окружения), чтобы файл содержал данные только одной инсталляции.

Следуя этим шагам, код и зависимости остаются общими, а конфигурация, контейнеры и данные полностью изолированы между ботами.




## Резервные копии

Для экспорта/импорта данных Redis предусмотрен скрипт `scripts/redis_backup.py`. Он сохраняет:
- hash `users` (весь профиль пользователя, статус тикета, silent-mode, язык и т.п.);
- hash `settings` (кастомные приветствия и сообщения закрытия);
- индексы `users_index_*` (связь ID темы ↔ ID пользователя).

```bash
# Сделать бэкап в файл backup-$(date).json
python scripts/redis_backup.py backup backups/support-bot-$(date +%F).json

# Восстановить данные из бэкапа
python scripts/redis_backup.py restore backups/support-bot-2025-10-20.json
```

Скрипт читает параметры подключения из `.env` (`REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, опционально `REDIS_PASSWORD`). При восстановлении целевые hash'и предварительно очищаются.

## Технологии

- Python 3.12, [aiogram](https://docs.aiogram.dev) 3.x;
- Redis + APScheduler для хранения состояния и напоминаний;
- Docker Compose в качестве рекомендованного окружения.

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
