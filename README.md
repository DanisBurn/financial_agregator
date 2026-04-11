# Financial Aggregator

Финансовый агрегатор для рынка Узбекистана. Проект собирает курсы валют коммерческих банков и CBU, цены золотых слитков, прогнозы моделей `USD/EUR`, показывает их на сайте, в Telegram Mini App и в Telegram-боте.

## Распределение ролей в команде

- Бурнашев Данис и Овчаренко Владислав — Fullstack development
- Дубровская Амалия — ML engineering
- Усмонов Нодир — Telegram Bot development

## Что входит в проект

- `web` — Django-сайт и Telegram Mini App.
- `bot` — Telegram-бот с кнопкой открытия Mini App и текстовым режимом.
- `updater` — фоновый процесс на базе `main_server.py`, который обновляет данные и пишет их в MongoDB.
- `MongoDB` — основное хранилище курсов валют, золота, прогнозов и недельной истории CBU.
- `SQLite` — служебная база Django для сессий, локализации и модели пользователя Mini App.

## Архитектура

Поток данных выглядит так:

1. `main_server.py` получает данные с парсеров банков и CBU.
2. Данные сохраняются в `currency_rates.json`, затем дополняются прогнозами из `prediction/`.
3. Обновленный отчет отправляется в MongoDB.
4. Сайт и Mini App читают данные из MongoDB.
5. Telegram-бот тоже читает данные из MongoDB, а не запускает парсеры сам.

Это важно: единый источник данных для сайта, Mini App и бота сейчас один — MongoDB. Ручное или автоматическое обновление происходит через `main_server.py`.

## Структура репозитория

```text
financial_agregator/
├── banks/                  # парсеры банков
├── bot/                    # Telegram-бот
├── docker/                 # startup scripts для контейнеров
├── prediction/             # модели и логика прогноза
├── web/                    # Django сайт и Mini App
├── main.py                 # однократное обновление отчета
├── main_server.py          # почасовое обновление в цикле
├── docker-compose.yml      # быстрый локальный запуск всего проекта
├── Dockerfile              # единый image для web, bot и updater
├── fly.toml                # Fly.io config для web + Mini App
├── fly.bot.toml            # Fly.io config для Telegram-бота
├── fly.updater.toml        # Fly.io config для updater
└── .env.example            # шаблон переменных окружения
```

## Требования

- Docker 24+ и Docker Compose plugin
- или Python 3.12, если запускать без Docker
- Telegram bot token от `@BotFather`
- MongoDB URI
  - для локального Docker запуска можно использовать встроенный контейнер MongoDB
  - для production рекомендуется внешний MongoDB Atlas

## Переменные окружения

Скопируйте шаблон:

```bash
cp .env.example .env
```

Минимально нужно заполнить:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,testserver,web
SQLITE_PATH=/data/db.sqlite3
WEB_PORT=8886
WEB_CONCURRENCY=2
GUNICORN_TIMEOUT=120

TELEGRAM_BOT_TOKEN=123456789:AA...
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_AUTH_MAX_AGE=86400

MINIAPP_URL=http://localhost:8886/miniapp/
MINIAPP_DEFAULT_LANGUAGE=ru

MONGO_URI=
```

Пояснения:

- `MONGO_URI=`
  - если оставить пустым и запускать через `docker compose`, проект автоматически подключится к локальному контейнеру `mongo`
  - если указать внешний URI, будет использоваться он
- `MINIAPP_URL`
  - для локального запуска можно оставить `http://localhost:8886/miniapp/`
  - для реального Telegram Mini App нужен публичный `https://.../miniapp/`
- `SQLITE_PATH`
  - нужен для внутренней Django-базы, это не замена MongoDB

## Быстрый запуск через Docker

Это основной способ быстро развернуть весь проект локально.

### 1. Подготовить `.env`

```bash
cd /home/user/py_project/financial_agregator
cp .env.example .env
```

Заполните в `.env`:

- `DJANGO_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- при необходимости `MONGO_URI`

### 2. Собрать и запустить все сервисы

```bash
docker compose up -d --build
```

Будут запущены:

- `mongo`
- `web`
- `bot`
- `updater`

### 3. Проверить состояние

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f updater
docker compose logs -f bot
```

### 4. Открыть сайт

```text
http://localhost:8886/
http://localhost:8886/miniapp/
```

### 5. Остановить проект

```bash
docker compose down
```

Если нужно остановить и удалить volume MongoDB/SQLite:

```bash
docker compose down -v
```

## Что делает каждый контейнер

- `web`
  - запускает Django через Gunicorn
  - выполняет `migrate`
  - отдает сайт и Mini App
- `bot`
  - запускает `bot/bot.py`
  - читает данные из MongoDB
  - открывает Mini App через кнопку
- `updater`
  - запускает `main_server.py`
  - обновляет данные сразу после старта и потом раз в час
- `mongo`
  - хранит валютные курсы, золото, прогнозы и историю CBU

## Ручное обновление данных

### Через Docker

Разовое ручное обновление:

```bash
docker compose exec updater python -c "import main_server; main_server.refresh_report_server(verbose=True)"
```

Посмотреть логи updater:

```bash
docker compose logs -f updater
```

### Без Docker

Из корня проекта:

```bash
/home/user/py_project/.venv/bin/python -c "import main_server; main_server.refresh_report_server(verbose=True)"
```

## Локальный запуск без Docker

Если нужен запуск напрямую через Python:

```bash
cd /home/user/py_project/financial_agregator
/home/user/py_project/.venv/bin/pip install -r requirements.txt
/home/user/py_project/.venv/bin/python web/manage.py migrate
/home/user/py_project/.venv/bin/python web/manage.py check
/home/user/py_project/.venv/bin/pytest -q
```

Отдельный запуск сервисов:

```bash
/home/user/py_project/.venv/bin/python web/manage.py runserver 127.0.0.1:8886
/home/user/py_project/.venv/bin/python bot/bot.py
/home/user/py_project/.venv/bin/python main_server.py
```

## Деплой на Fly.io

Проект разбит на три отдельных Fly app:

- `kursuz-web` — сайт и Mini App
- `kursuz-bot` — Telegram-бот
- `kursuz-updater` — hourly updater с `main_server.py`

### 1. Установить `flyctl`

```bash
curl -L https://fly.io/install.sh | sh
source ~/.bashrc
fly auth login
```

### 2. Создать apps

```bash
fly apps create kursuz-web
fly apps create kursuz-bot
fly apps create kursuz-updater
```

### 3. Создать volume для `kursuz-web`

```bash
fly volumes create data --region arn --size 1 --app kursuz-web
```

### 4. Задать secrets

Для `kursuz-web`:

```bash
fly secrets set -a kursuz-web \
  DJANGO_SECRET_KEY="your-secret-key" \
  TELEGRAM_BOT_TOKEN="your-bot-token" \
  TELEGRAM_BOT_USERNAME="your_bot_username" \
  TELEGRAM_AUTH_MAX_AGE="86400" \
  MONGO_URI="your_mongo_uri"
```

Для `kursuz-bot`:

```bash
fly secrets set -a kursuz-bot \
  TELEGRAM_BOT_TOKEN="your-bot-token" \
  TELEGRAM_BOT_USERNAME="your_bot_username" \
  MINIAPP_URL="https://kursuz-web.fly.dev/miniapp/" \
  MINIAPP_DEFAULT_LANGUAGE="ru" \
  MONGO_URI="your_mongo_uri"
```

Для `kursuz-updater`:

```bash
fly secrets set -a kursuz-updater \
  MONGO_URI="your_mongo_uri"
```

### 5. Деплой

```bash
fly deploy --config fly.toml --remote-only
fly deploy --config fly.bot.toml --remote-only
fly deploy --config fly.updater.toml --remote-only
```

### 6. Проверка

```bash
fly status -a kursuz-web
fly status -a kursuz-bot
fly status -a kursuz-updater

fly logs -a kursuz-web
fly logs -a kursuz-bot
fly logs -a kursuz-updater
```

## Как обновлять код на Fly.io

После изменений в коде выполняйте деплой только нужного сервиса:

```bash
fly deploy --config fly.toml --remote-only
fly deploy --config fly.bot.toml --remote-only
fly deploy --config fly.updater.toml --remote-only
```

Соответствие:

- `fly.toml` — сайт и Mini App
- `fly.bot.toml` — Telegram-бот
- `fly.updater.toml` — `main_server.py`

## Telegram Mini App

Для реального запуска через Telegram нужен публичный HTTPS URL.

После деплоя:

1. Создайте бота через `@BotFather`
2. Получите `token` и `username`
3. Запишите их в `Fly secrets`
4. В `@BotFather` настройте `Menu Button`
5. Укажите URL:

```text
https://kursuz-web.fly.dev/miniapp/
```

После этого:

- бот покажет кнопку открытия Mini App
- Telegram откроет Django-страницу внутри WebApp
- авторизация Mini App пройдет через `initData`

## Проверка состояния после запуска

Что должно работать:

- сайт открывается по `/`
- Mini App entrypoint открывается по `/miniapp/`
- `kursuz-updater` пишет свежие данные в MongoDB
- бот показывает данные из MongoDB
- `/refresh` в боте перечитывает базу, а не запускает парсеры

## Полезные команды

Проверка Python-кода:

```bash
/home/user/py_project/.venv/bin/python -m py_compile main.py main_server.py bot/bot.py
```

Проверка Django:

```bash
/home/user/py_project/.venv/bin/python web/manage.py check
```

Тесты:

```bash
/home/user/py_project/.venv/bin/pytest -q
```

