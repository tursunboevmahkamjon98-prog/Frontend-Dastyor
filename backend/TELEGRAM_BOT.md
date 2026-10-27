# Dastyor Telegram bot

Two bots, one process.

* The **public bot** is what teachers use. It links their Dastyor
  account to their Telegram chat, shows their balance and their
  operation history, and tells them where to transfer money.
* The **admin bot** is where an administrator credits a balance. It is a
  separate bot so that the credit buttons do not exist in the public
  bot's update stream at all.

Both are served by one long-polling worker, `app/telegram/bot.py`, run
as its own container.

---

## What credits a balance, and what does not

**An administrator credits a balance. Nothing else does.**

The administrator checks their bank app, sees the money, and records it
in the bot. The bot does not have access to any bank account and cannot
confirm a transfer. Neither can OCR: a receipt screenshot can be
fabricated, re-sent, or belong to somebody else's transfer, so a scan is
at most a hint about what to look for.

A teacher may still send a photo of a receipt — it makes them easier to
find in a list — but it is optional and it credits nothing on its own.

## Money is integer dirams

1 somoni = 100 dirams. Every amount in the database, in the service
layer and in the ledger is an `int` number of dirams. `Decimal` is used
to parse what an admin types and is converted to dirams immediately.
There is no `float` anywhere in the path, because `0.1 + 0.2` is not
`0.3` in binary floating point and this is money.

`parse_amount` accepts `25`, `25.50`, `25,50`, `1 000,25`. It rejects
`1e5`, `25.555`, `0x10`, `--5`, full-width digits, and anything else
that is not a plain decimal: an amount nobody typed on purpose must
never be guessed at.

---

## Configuration

`TELEGRAM_BOT_TOKEN` and the rest of the variables below live in
`backend/.env` — the same **committed** file every other secret in this
repo (AI keys, SMS credentials) already lives in, because the only
deploy path available is `git pull` with no way to write a second file
to the server by hand. This is a deliberate change (2026-10-24, was
previously `backend/.env.telegram`, gitignored) made for that reason,
not an oversight — see the comment on `TELEGRAM_BOT_TOKEN` in
`backend/.env` and on the `telegram-bot` service in `docker-compose.yml`.

If a deploy path that CAN write a second file to the server becomes
available later, `backend/.env.telegram` (gitignored, template in
`.env.telegram.example`) still works and overrides `.env` for anything
it sets — `app/telegram/config.py` reads `.env` first and
`.env.telegram` second. That split is the better default when it is
reachable; it just was not reachable here.

| Variable | Required | What it is |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | The public bot's token from @BotFather. |
| `TELEGRAM_BOT_USERNAME` | yes | Public bot's @name, without the `@`. Used to build deep links. |
| `TELEGRAM_ADMIN_BOT_TOKEN` | no | A **second** bot's token. Empty keeps single-bot mode, where admin commands are served by the public bot and refused for everyone else. |
| `TELEGRAM_ADMIN_IDS` | yes | Comma-separated numeric Telegram user ids of the root administrators. These cannot be removed from inside the bot. |
| `TELEGRAM_ADMIN_LANGUAGE` | no | `ru` (default), `tg` or `en`. The admin channel is one language. |
| `TELEGRAM_PAY_INSTRUCTIONS` | no | Where teachers transfer money. Inserted verbatim and **not** translated — write it in the language your teachers read. An admin can change it at runtime with `/paycontrol`, which takes precedence. |
| `TELEGRAM_PAY_RECIPIENT` | no | The expected recipient name, used only to flag a receipt that names somebody else. |
| `TELEGRAM_MAX_TOPUP_DIRAMS` | no | Ceiling for a single operation, in dirams. Default `500000` (5 000 somoni). Enforced in `topup.credit_user`, not only in the bot, so it holds even if a caller skips the conversation. |

The token never appears in Flutter code, in the web frontend, or in a
log: `app/telegram/api.py` installs a scrubber that rewrites anything
token-shaped to `<BOT_TOKEN>` before it reaches the logger. It DOES now
appear in `backend/.env`, committed, per the section above.

**If a token has ever been shown to anyone outside this private repo
(pasted in a chat, a public issue, a log viewed elsewhere), revoke it**
in @BotFather (`/mybots` → the bot → API Token → Revoke) and put the new
one in `.env`. Revoking is the only thing that stops an exposed token
being a usable credential.

---

## Running it

### On the server

```sh
git pull
docker compose up -d --build
docker compose logs -f telegram-bot
```

`telegram-bot` starts with the other three services now — no separate
profile or command. Exactly one replica — two pollers would both call
`getUpdates` and every teacher would get every message twice
(`tests/test_telegram_startup.py` guards the one way this could happen
by accident: `TELEGRAM_ADMIN_BOT_TOKEN` set equal to `TELEGRAM_BOT_TOKEN`).

### On Windows, for development

```powershell
cd backend
.\venv313\Scripts\python.exe -m app.telegram.bot
```

Pass the config through `.env` / `.env.telegram` rather than the shell:
PowerShell 5.1 reads a BOM-less `.ps1` as ANSI and will mangle Cyrillic
in a literal, which is how `ТЕСТОВЫЙ` once arrived as `РўР•РЎРўРћР’Р«Р™`.

### Checking the configuration without sending anything

```powershell
.\venv313\Scripts\python.exe scripts\telegram_bootstrap.py check
.\venv313\Scripts\python.exe scripts\telegram_bootstrap.py whoami
```

`check` validates the shape of what is configured and prints a redacted
summary. `whoami` calls `getMe` for each configured bot. Neither sends a
message to anyone.

---

## The administrator's flow

`➕ Начислить средства` (or `/credit`):

1. **Who.** Reply with the 6-digit Dastyor account id, a phone number,
   or part of a name. An exact id or phone match is taken; a name match
   returns a list to pick from and never auto-selects, because crediting
   the wrong person is the mistake this flow must not make easy.
2. **Check.** The bot echoes the name, the account id and the current
   balance.
3. **How much.** A number. Rejected amounts say why — not a number, not
   positive, above the ceiling — and the step stays open.
4. **Comment.** Free text, or `/skip`. Stored as the ledger reason.
5. **Confirm.** A preview showing balance before, amount, balance after,
   and the comment. The balance is re-read at this point: a generation
   charge may have landed since step 2.
6. `✅ Подтвердить начисление` applies it. `❌ Отмена` applies nothing.

`/cancel` abandons the flow at any step. A button tap always wins over
whatever step is waiting for text, so an admin who changes their mind is
never stuck.

### Reviewing a receipt

When a teacher's receipt arrives (step 3 of their flow, below), every
configured administrator gets a message with the photo, the OCR read-out,
and four buttons:

| Button | What it does |
| --- | --- |
| `✅ Подтвердить оплату` | One tap. Credits exactly what the request asked for — the figure tied to this request's own idempotency key, not retyped. |
| `❌ Отклонить оплату` | Asks for a reason, then rejects. The teacher sees that reason verbatim. Credits nothing. |
| `💵 Указать другую сумму` | For when the receipt shows a different figure than requested. The admin types the real one; it is audited as `approved_with_correction` with both numbers. |
| `🔎 Нужна доп. проверка` | Sends the teacher back for a clearer receipt. Leaves the request open — not approved, not rejected. |

All four are compare-and-swap against the request's own status, so a
second admin tapping a stale message, or the same admin tapping twice,
changes nothing the second time.

### Other admin commands

| Command | Button | What it does |
| --- | --- | --- |
| `/credit` | ➕ Начислить средства | The flow above. |
| `/finduser` | 👥 Найти пользователя | Look up a user and their balance. Credits nothing. |
| `/topups` | 📋 История начислений | The last credits made through the bot. |
| `/stats` | 📊 Статистика | Counts and totals for today, this month and overall. |
| `/cancel` | ❌ Отмена | Abandon whatever is in progress. |
| `/pending` | 🧾 Заявки с чеками | The optional receipt queue. |
| `/paycontrol` | 💳 Реквизиты | Set the payment details teachers are shown. |
| `/admins`, `/addadmin`, `/deladmin` | 👤 Администраторы | Manage who can credit. Every grant and revoke is written to the audit log. |

A granted administrator cannot credit themselves. A root administrator
(one listed in `TELEGRAM_ADMIN_IDS`) can, but it is audited as
`approved_self` and tagged in the ledger reason.

## The teacher's flow

Every teacher-facing message, button and notification is Russian,
regardless of the account's own `language` setting — the public bot is
pinned to it via `teacher_lang()` in `app/telegram/texts.py`. (The admin
channel is separately pinned to Russian via `TELEGRAM_ADMIN_LANGUAGE`,
unaffected by this.) The five main-panel buttons:

| Button | Command | What it shows |
| --- | --- | --- |
| 💳 Пополнить баланс | `/pay` | Where to transfer, the account id to quote, and asks for the receipt photo. |
| 📊 Мой баланс | `/balance` | Current balance and the price of one material. |
| 🧾 Проверить статус платежа | `/status` | Every open and recent request, with its status (⏳ ожидает проверки, 🔍 проверяется, ✅ подтверждён, ❌ отклонён). |
| 📜 История платежей | `/history` | Credits and charges together, newest first, with the balance underneath. |
| ❓ Помощь | `/help` | The four steps, and why a photo alone credits nothing. |

`👤 Мой аккаунт` (name, Dastyor id, balance, link status) is still real
and still reachable by typing `/account` — it is just not one of the
five buttons shown, to match the panel exactly.

Linking is normally done from the app: Balance → "Top up via Telegram"
issues a single-use token and opens the bot. Where `t.me` is blocked by
an ISP, `/login` links by phone and password instead; the password
message is deleted from the chat immediately, whether or not it was
correct.

---

## Guarantees, and how they are enforced

**Exactly once.** Every confirmation carries an idempotency key. The key
is checked before the write, the write is guarded by the partial unique
index `uq_balance_tx_idempotency`, and a loser of that race reads the
winning row rather than retrying. Tapping confirm twice credits once;
five simultaneous confirmations credit once.

**Atomic.** `UPDATE users SET balance_dirams = balance_dirams + :amt ...
RETURNING balance_dirams` is the read-modify-write, so `balance_before`
is derived from the same statement that wrote it. A separate read could
see a different value under a concurrent charge.

**The ledger explains the balance.** Credits are written to the existing
`balance_transactions` table, not a parallel one, because that row is
already the single source of truth for a balance and the first time two
tables disagreed nobody would know which was right. The new columns are
`actor_telegram_id`, `idempotency_key` and `public_code`.

`topup.reconcile_balance(user_id)` reports `stored`, `from_ledger` and
`unexplained`. A **constant** non-zero difference is an opening balance
from before the ledger existed. A **growing** difference is a bug.

**A failed notification never undoes a credit.** By the time the teacher
is told, the money has moved. A transport failure is retried three times
with a short backoff; a refusal from Telegram ("bot was blocked by the
user") is not retried, because it will refuse again. Either way the
credit stands, the admin is told the notice did not arrive, and the
teacher still sees it in their own history.

**Authorization is on the sender, never the payload.** A callback is
authorized against the configured admin list, so holding a button
someone else was shown achieves nothing.

---

## Tests

From `backend/`:

```powershell
.\venv313\Scripts\python.exe tests\test_telegram_unit.py
.\venv313\Scripts\python.exe tests\test_telegram_payments.py
.\venv313\Scripts\python.exe tests\test_telegram_topup.py
```

`test_telegram_unit.py` needs nothing — no database, no network, no
tesseract. The other two need a real Postgres: the guarantees under test
*are* Postgres behaviour (compare-and-swap, partial unique indexes, row
locking under concurrency), and SQLite would pass while proving nothing.
They create and use `dastyor_bot_test`, derived from `DATABASE_URL`, so
development data is never touched. Override the name with
`TELEGRAM_TEST_DATABASE`.

No test reaches Telegram, makes a payment, or messages a real
administrator. The Bot API client is a recording fake and receipt scans
are built from text fixtures.
