# Support Bot

[![License](https://img.shields.io/github/license/mrtesla07/support-bot)](LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Bot-grey?logo=telegram)](https://core.telegram.org/bots)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Redis](https://img.shields.io/badge/Redis-enabled?logo=redis&color=red)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://www.docker.com/)

Support Bot — телеграм‑бот для обработки обращений пользователей и проксирования диалогов в модуль поддержки.
Бот работает в личных сообщениях, пересылая обращения в тематический топик форума группы и синхронизируя статусы через Redis.

## Возможности

- автоматическое создание и ведение форумных тредов для каждого пользователя;
- передача сообщений и мультимедиа между пользователем и агентами поддержки;
- автоматические напоминания агентам о необработанных диалогах;
- встроенные команды модерации (/resolve, /silent, /ban, /information);
- защита от вредоносных профилей: фильтры ссылок/инвайтов, авто‑бан и авто‑санитация отображаемых имён.

## Быстрый старт

`ash
cp .env.example .env
nano .env   # заполните токен бота и параметры Redis

pip install -r requirements.txt
python -m app
`

### Запуск в Docker

`ash
docker compose up -d --build
`

## Обновление и миграции

При обновлении придерживайтесь последовательности:

`ash
docker compose down
git pull
docker compose up -d --build
`

Параметр --build пересоберёт образ и применит изменения из 
equirements.txt. После перезапуска сможете посмотреть логи:

`ash
docker compose logs -f bot
`

Данные Redis хранятся в volume и не удаляются, пока вы явно не выполните docker compose down -v или не удалите том вручную.

При старте бот выполняет миграции из pp/migrations:

1. обновляет версии пользователей в Redis;
2. санирует отображаемые имена и переименовывает форумные топики при необходимости;
3. может расширяться новыми миграциями по мере развития.

## Переменные окружения

| Имя                | Описание                                 |
|--------------------|------------------------------------------|
| BOT_TOKEN        | токен Telegram‑бота                      |
| BOT_DEV_ID       | ID администратора                        |
| BOT_GROUP_ID     | ID чата‑форума для поддержки             |
| BOT_EMOJI_ID     | кастомная иконка для темы                |
| BOT_RESOLVED_EMOJI_ID | иконка для закрытых тикетов        |
| REDIS_HOST       | хост Redis                               |
| REDIS_PORT       | порт Redis                               |
| REDIS_DB         | номер базы Redis                         |

## Тестирование

`ash
pytest
`

Тесты покрывают сервисные функции (санитация имён, хранилище настроек, окна интерфейса).

## Стек

- Python 3.12 + aiogram 3;
- Redis для хранения состояния;
- APScheduler для напоминаний;
- Docker Compose для развёртывания.

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE).
