# 🤖 Support Bot

[![License](https://img.shields.io/github/license/tonmendon/ton-subdomain)](https://github.com/tonmendon/ton-subdomain/blob/main/LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Bot-grey?logo=telegram)](https://core.telegram.org/bots)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![Redis](https://img.shields.io/badge/Redis-Yes?logo=redis&color=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-blue?logo=docker&logoColor=white)](https://www.docker.com/)

**Support Bot** — это телеграм-бот для организации поддержки пользователей. Он автоматически создаёт темы в форуме группы, поэтому диалоги не смешиваются, а модераторы всегда видят контекст. Бот помогает блокировать нежелательных собеседников, включать «тихий» режим, отправлять информативные ответы и поддерживать порядок в переписке.

Бот напомнит команде, если пользователю не ответили в течение 5 минут, и позволяет закрывать обсуждение командой `/resolve`.

* Bot example: @nessshonSupportBot
* Linked group example: @nessshonSupportGroup

**О лимитах**:
<blockquote>
Официальных ограничений нет, но сообщество делится ориентировочными цифрами.<br>
• Создание новых тем — до <b>~20</b> в минуту.<br>
• Общее количество тем — до <b>~1 000 000</b>.
</blockquote>

<details>
<summary><b>Команды для администратора (DEV_ID)</b></summary>

* `/newsletter` — открыть меню рассылки.

  Через это меню можно запускать рассылки по пользователям.
  **Важно**: команда доступна только в личных сообщениях.

</details>

<details>
<summary><b>Команды в темах группы</b></summary>

* `/ban` — заблокировать или разблокировать пользователя. Управляет тем, доходят ли сообщения до команды поддержки.
* `/silent` — включить или выключить тихий режим. В тихом режиме ответы не отправляются пользователю.
* `/information` — показать информацию о пользователе: ID, имя, юзернейм, статус и дату регистрации.
* `/resolve` — отметить тикет решённым и отключить напоминания.

</details>

## Как начать

<details>
<summary><b>Подготовка</b></summary>

1. Создайте бота через [@BotFather](https://t.me/BotFather) и сохраните токен (`BOT_TOKEN`).
2. Настройте группу и включите в ней темы.
3. Добавьте бота в группу с правами администратора и разрешите управление темами.
4. Пригласите в группу бота [What’s my Telegram ID?](https://t.me/my_id_bot), чтобы узнать ID группы (`BOT_GROUP_ID`).
5. При необходимости измените тексты бота в файле [texts](https://github.com/mrtesla07/support-bot/tree/main/app/bot/utils/texts.py).
6. Чтобы добавить новые языки, дополните [SUPPORTED_LANGUAGES](https://github.com/mrtesla07/support-bot/tree/main/app/bot/utils/texts.py#L5) и соответствующие блоки в [data](https://github.com/mrtesla07/support-bot/tree/main/app/bot/utils/texts.py#L33).

</details>

<details>
<summary><b>Установка</b></summary>

Понадобится собственный сервер или арендованный хостинг. Проще всего развернуть бота в Docker.

1. Клонируйте репозиторий:

    ```bash
    git clone https://github.com/mrtesla07/support-bot.git
    ```

2. Перейдите в каталог проекта:

    ```bash
    cd support-bot
    ```

3. Скопируйте файл переменных окружения:

    ```bash
    cp .env.example .env
    ```

4. Заполните [.env](#переменные-окружения) своими значениями:

    ```bash
    nano .env
    ```

5. Запустите контейнеры:

    ```bash
    docker-compose up --build
    ```

</details>

## Переменные окружения

<details>
<summary>Развернуть список</summary>

| Переменная      | Тип  | Описание                                              | Пример               |
|-----------------|------|-------------------------------------------------------|----------------------|
| `BOT_TOKEN`     | `str`| Токен бота от [@BotFather](https://t.me/BotFather)    | `123456:qweRTY`      |
| `BOT_DEV_ID`    | `int`| Telegram ID разработчика или администратора           | `123456789`          |
| `BOT_GROUP_ID`  | `str`| ID группы, в которой работает бот                     | `-100123456789`      |
| `BOT_EMOJI_ID`  | `str`| ID кастомного эмодзи для иконки темы                  | `5417915203100613993`|
| `REDIS_HOST`    | `str`| Хост или IP сервера Redis                             | `redis`              |
| `REDIS_PORT`    | `int`| Порт Redis                                            | `6379`               |
| `REDIS_DB`      | `int`| Номер базы Redis                                      | `1`                  |

<details>
<summary>Список поддерживаемых кастомных эмодзи</summary>

Справочный список emoji ID оставлен в исходном репозитории и может использоваться при настройке тем.

</details>

</details>


## Донаты

**TON** — `EQC-3ilVr-W0Uc3pLrGJElwSaFxvhXXfkiQA3EwdVBHNNess`

**USDT** (TRC-20) — `TDHMG7JRkmJBDD1qd4bNhdfoy2uzVd8ixA`

## Как помочь проекту

Нашли ошибку или хотите добавить функциональность — создайте issue или отправьте pull request.

## Лицензия

Проект распространяется по [MIT License](LICENSE). Используйте, изменяйте и распространяйте код в рамках условий лицензии.
