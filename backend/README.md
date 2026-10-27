# Dastyor backend: первый запуск Telegram-пополнения

Backend работает в `C:\Users\user\Desktop\dastyor\backend`, отдельный бот — в `C:\Users\user\Desktop\dastyor-telegram-bot`. Бот использует только защищённый HTTP API. PostgreSQL и backend являются источником истины для баланса и решений по заявкам.

## Переменные окружения

Настройки читаются из `backend/.env`, затем из `backend/.env.telegram`; переменные процесса имеют приоритет. **Для новых секретов используйте `.env.telegram` или окружение процесса.** `.env.telegram` исключён из Git, а существующий `backend/.env` в этом репозитории отслеживается Git. Не перезаписывайте существующие настройки. Пример только для отдельного бота: [.env.standalone.example](.env.standalone.example).

| Имя | Назначение и обязательность |
| --- | --- |
| `DATABASE_URL` | Обязательно: URL PostgreSQL с асинхронным драйвером `postgresql+asyncpg` для Python 3.13 |
| `DATABASE_URL_SYNC` | Обязательно: синхронный URL PostgreSQL для Alembic; тот же сервер, порт, БД и учётные данные |
| `SECRET_KEY` | Обязательно: существующий ключ авторизации Dastyor; не меняйте его ради запуска бота |
| `AI_API_KEY` | Обязательно для загрузки текущего backend; Telegram-платежи его не используют |
| `DASTYOR_BOT_API_TOKEN` | Обязательно для бота: отдельный случайный сервисный секрет не короче 32 символов; совпадает с одноимённой настройкой бота |
| `DASTYOR_STANDALONE_TELEGRAM_TOKEN` | Обязательно: токен отдельного BotFather-бота; совпадает с `TELEGRAM_BOT_TOKEN` в проекте бота |
| `DASTYOR_STANDALONE_BOT_USERNAME` | Обязательно: настоящий username этого бота |
| `DASTYOR_BOT_ROOT_ADMIN_ID` | Обязательно: проверенный числовой Telegram ID владельца; совпадает с `BOOTSTRAP_ADMIN_ID` в боте |
| `CORS_ORIGINS` | Адрес web-приложения, если браузер обращается к backend с другого origin |
| `TELEGRAM_MAX_TOPUP_DIRAMS` | Необязательно: серверный предел одной заявки в дирамах; 100 дирамов = 1 сомони |
| `TELEGRAM_LINK_TOKEN_TTL_SECONDS` | Необязательно: срок одноразовой ссылки |
| `CARD_ENCRYPTION_KEY` | Нужен при использовании раздела банковских карт в CRM; не требуется для самого Telegram-процесса с реквизитами из настроек бота |

Не используйте один токен Telegram одновременно для старого polling-процесса и отдельного бота. `DASTYOR_BOT_API_TOKEN` должен отличаться от токена Telegram. Настройки SMS/почты/Google для входа в Dastyor остаются настройками соответствующих провайдеров; не заменяйте их тестовыми значениями на рабочем сервере.

## Windows: проверка и запуск

Откройте PowerShell. В текущей рабочей среде уже есть `backend/venv313`; повторно создавать его не нужно. На новой машине установите Python 3.13 и зависимости:

```powershell
Set-Location 'C:\Users\user\Desktop\dastyor\backend'
# Только если окружения ещё нет:
py -3.13 -m venv venv313
.\venv313\Scripts\python.exe -m pip install -r requirements.txt
# Только если приватного файла ещё нет:
if (-not (Test-Path -LiteralPath '.env.telegram')) {
    Copy-Item -LiteralPath '.env.standalone.example' -Destination '.env.telegram'
}
```

Заполните имена из таблицы в приватных настройках. URL должны указывать на одну БД. Для паролей со специальными символами используйте URL-кодирование. Существующий `.env.telegram` дополняйте, не заменяйте.

Проверка **без изменений БД**:

```powershell
.\venv313\Scripts\python.exe -m app.preflight --require-bot
.\venv313\Scripts\python.exe -m app.preflight --database --allow-pending-migrations
.\venv313\Scripts\python.exe -m alembic heads
```

Проверка печатает только имена параметров, статусы и номера ревизий. Она открывает транзакцию `READ ONLY`, сверяет пару URL, доступность PostgreSQL, структуру и историю миграций. Она не проверяет баланс и не зачисляет деньги. Ошибка частичной конфигурации бота останавливает запуск. Если бот полностью отключён, обычный backend может работать; `start-backend.ps1` требует полностью настроенный Telegram-процесс.

Перед первым применением миграций сохраните резервную копию рабочей БД обычным способом. Следующая команда **изменяет схему**, поэтому выполняйте её только для выбранной БД:

```powershell
.\venv313\Scripts\python.exe -m app.db_bootstrap
.\venv313\Scripts\python.exe -m app.preflight --require-bot --database
.\venv313\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Адрес локального backend: `http://127.0.0.1:8001`. Остановить — Ctrl+C. Для доступа из интернета нужен HTTPS reverse proxy. В текущей Windows выполнение `.ps1` запрещено политикой; приведённые команды Python не требуют изменения этой политики. На машине, разрешающей PowerShell-скрипты, можно использовать `./start-backend.ps1 -Migrate`: он проверяет настройки, применяет миграции и запускает сервер. Без `-Migrate` скрипт не применяет миграции автоматически.

Миграции Telegram добавляют поля идемпотентности, тип чека, таблицу прав и отметку доставки уведомления. Они не меняют пользовательские балансы. Уже созданная ORM таблица `standalone_bot_admins` сохраняется только при совпадении ожидаемой структуры. Для существующей БД без истории Alembic и при расхождении схемы запуск останавливается: **не применяйте `stamp head` для обхода ошибки**. Пустая БД инициализируется перед отметкой ревизии.

## Запуск бота

В отдельном PowerShell следуйте [README бота](../../dastyor-telegram-bot/README.md). Для первоначального получения ID используется `dastyor_bot.py --bootstrap-only`: только `/whoami` и `/start`, без платёжных обработчиков. После проверки ID через доверенный канал запишите его в оба проекта, запустите backend и выполните в папке бота:

```powershell
.\.venv\Scripts\python.exe dastyor_bot.py --check-config
.\.venv\Scripts\python.exe dastyor_bot.py --check-services
.\.venv\Scripts\python.exe dastyor_bot.py
```

Проверка сервисов вызывает только Telegram `getMe`, `getWebhookInfo` и защищённый `GET /api/bot/v1/health`. Она сверяет username/ID бота, ID владельца, сервисную авторизацию и предел сумм. Она не удаляет webhook, не отправляет сообщений и не создаёт платежей. После полного запуска владелец должен отправить `/start`, чтобы сохранить роль в локальном хранилище бота.

## Автоматические и реальные проверки

```powershell
Set-Location 'C:\Users\user\Desktop\dastyor\backend'
.\venv313\Scripts\python.exe -m pytest -q tests
.\venv313\Scripts\python.exe -m pytest -q unit_tests
Set-Location 'C:\Users\user\Desktop\dastyor-telegram-bot'
.\.venv\Scripts\python.exe -m pytest -q tests
```

`backend/tests/conftest.py` использует отдельную локальную тестовую БД и тестовые ключи. Он отказывается работать с основной БД. Telegram-запросы в новых тестах подменяются; подтверждения и отказы меняют только тестовые записи. Старые сценарии `test_teacher_flow.py` и `test_api_guards.py` требуют специально запущенный изолированный сервер: не запускайте их с рабочими настройками. Они могут создавать пользователей и выполнять операции backend.

С настоящим Telegram и работающим backend ещё нужно проверить: открытие ссылки с кнопки Dastyor, `/start` владельца, выбор языка, доставку настоящего чека, доступ администратора и получение уведомлений. Для реального подтверждения администратор должен увидеть реальный поступивший перевод в банке. Повторное подтверждение, отклонение и сетевые сбои без перевода сначала проверяйте на отдельном тестовом аккаунте в staging. Успешные автоматические тесты не означают, что реальный платёж уже проверен.
