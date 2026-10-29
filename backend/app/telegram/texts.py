"""Bot message catalogue, Tajik first.

Language selection reuses ``app.i18n``'s alias table rather than a second
one, so a user whose profile says "Тоҷикӣ", "tajik" or "tg" gets Tajik in
the bot for the same reason they get it in the app.

Tajik is the fallback for an unknown language here, not Russian as in
``app.i18n``: the app's error strings default to Russian for historical
reasons, but this flow is new and its audience is Tajik teachers.

No string in this file names a bank, an account number or a card. Those
come from ``TELEGRAM_PAY_INSTRUCTIONS``, which the owner writes. A
plausible-looking placeholder here would be a wrong destination for
somebody's money.

``normalize_lang`` itself stays a general-purpose tg/ru/en resolver —
``admin_t`` reuses it too, and an admin catalogue that could only ever
answer "ru" regardless of what was asked for would be the wrong kind of
pinning. Teacher-facing output is pinned to Russian at a narrower point:
``teacher_lang`` below, which every bot.py call site that used to read
``normalize_lang(account.language)`` for a teacher message now calls
instead. See its own docstring for why.
"""

from app.i18n import _LANG_ALIASES
from app.telegram.admin_ui import LABELS, HELP_TEXT


def normalize_lang(language: str | None) -> str:
    raw = (language or "").strip().lower()
    return _LANG_ALIASES.get(raw) or _LANG_ALIASES.get(raw[:2]) or "tg"


def teacher_lang(account_language: str | None = None) -> str:
    """The language a teacher-facing message is written in.

    Pinned to Russian — the implementation brief this bot follows
    requires every user-facing message, button and notification to be
    Russian. ``account_language`` is accepted and ignored rather than
    dropped from call sites: if this policy is ever relaxed back to
    per-account language, every caller already passes the value that
    decision would need, and only this one function changes.
    """
    return "ru"


def fmt_somoni(dirams: int, lang: str = "tg") -> str:
    """Dirams to a somoni string, in the decimal convention of the locale."""
    text = f"{dirams / 100:.2f}"
    if lang in ("tg", "ru"):
        text = text.replace(".", ",")
    return text


MESSAGES: dict[str, dict[str, str]] = {
    "tg": {
        "currency": "сомонӣ",

        "start_unlinked": (
            "Салом! 👋\n\n"
            "Ман боти пардохти Dastyor ҳастам. Ман ба шумо кӯмак мекунам, "
            "ки тавозуни худро пур кунед.\n\n"
            "Аввал ҳисоби худро пайваст кунем.\n"
            "Тугмаи «🔑 Ворид шудан»-ро зер кунед — ҳамон рақами телефон ва "
            "паролеро, ки бо онҳо ба Dastyor ворид мешавед, пурсида мешавад.\n\n"
            "Ҳамин тавр. Дигар чизе лозим нест."
        ),
        "start_linked": (
            "✅ Тайёр! Ҳисоби шумо пайваст шуд.\n\n"
            "👤 {account}\n"
            "💰 Тавозун: {balance} {currency}\n\n"
            "Акнун аз тугмаҳои поён истифода баред 👇"
        ),
        "start_already_linked": (
            "👤 {account}\n"
            "💰 Тавозун: {balance} {currency}\n\n"
            "Аз тугмаҳои поён истифода баред 👇"
        ),
        "link_token_invalid": (
            "Пайванди пайвастшавӣ нодуруст аст.\n\n"
            "Барномаи Dastyor-ро кушоед ва аз «Тавозун» тугмаи «Пур кардани тавозун "
            "тавассути Telegram»-ро зер кунед — он пайванди нави дурустро месозад."
        ),
        "link_token_expired": (
            "Мӯҳлати пайванди пайвастшавӣ гузаштааст.\n\n"
            "Ин пайвандҳо кӯтоҳмуддатанд — ин барои амният аст. Дар барномаи "
            "Dastyor «Тавозун» -> «Пур кардани тавозун тавассути Telegram»-ро "
            "бори дигар зер кунед."
        ),
        "link_token_used": (
            "Ин пайванд аллакай истифода шудааст ва бори дуюм кор намекунад.\n\n"
            "Агар ин шумо набудед, фавран дар барнома пароли худро иваз кунед ва "
            "ба мо хабар диҳед. Барои пайвастшавии нав аз барнома пайванди нав гиред."
        ),
        "link_chat_taken": (
            "Ин чати Telegram аллакай ба ҳисоби дигари Dastyor пайваст аст.\n\n"
            "Агар ин иштибоҳ бошад, ба мо муроҷиат кунед — як чат ҳамзамон ба ду "
            "ҳисоб пайваст намешавад."
        ),

        "not_linked_short": (
            "Ҳисоби шумо пайваст нест. Барномаи Dastyor -> «Тавозун» -> "
            "«Пур кардани тавозун тавассути Telegram».\n"
            "/start — тавзеҳи муфассал"
        ),

        "help": (
            "Чӣ тавр тавозунро пур кунем:\n\n"
            "1️⃣  «➕ Пур кардани баланс»-ро зер кунед — ман рақами картаро медиҳам\n"
            "2️⃣  Пулро мефиристед\n"
            "3️⃣  ID Dastyor-и худро ба администратор мегӯед — он дар «👤 Ҳисоби ман» аст\n"
            "4️⃣  Администратор расидани пулро месанҷад ва тавозунро пур мекунад\n\n"
            "❗ Тавозун танҳо баъд аз он пур мешавад, ки администратор "
            "расидани пулро бо чашми худ бинад. Ин аз расидҳои "
            "сохта муҳофизат мекунад.\n\n"
            "📸 Фиристодани сурати расид ҳатмӣ нест, вале мумкин аст.\n\n"
            "Саволе ҳаст? Ба дастаи Dastyor нависед."
        ),

        "balance": (
            "👤 {account}\n"
            "💰 Тавозун: {balance} {currency}\n\n"
            "Ҳар як мавод {price} {currency} арзиш дорад."
        ),

        "pay_not_configured": (
            "Дастури пардохт ҳоло ба бот ворид нашудааст.\n\n"
            "Мо намехоҳем рақами тахминии ҳисоб нишон диҳем — пули шумо бояд ба "
            "ҷои дуруст равад. Лутфан ба дастаи Dastyor муроҷиат кунед."
        ),
        "pay_choose_amount": (
            "Чӣ қадар пул мефиристед?\n\n"
            "💰 Ҳозир: {balance} {currency}\n"
            "📄 Як мавод: {price} {currency}\n\n"
            "Яке аз тугмаҳоро зер кунед 👇\n"
            "Ё худатон рақам нависед, масалан: {example}"
        ),
        "pay_instructions": (
            "💳 Пулро ба ин ҷо фиристед:\n\n"
            "{instructions}\n\n"
            "Маблағ: {amount} {currency}\n"
            "Рақами дархост: {code}\n\n"
            "❗ ID Dastyor-и худро ба администратор гӯед: {account_id}\n"
            "Ӯ расидани пулро месанҷад ва тавозуни шуморо пур мекунад — "
            "ман дарҳол ба шумо менависам.\n\n"
            "📸 Фиристодани сурати расид ҳатмӣ нест. Агар фиристед, "
            "администратор шуморо осонтар меёбад."
        ),
        "amount_invalid": (
            "Маблағро нафаҳмидам. Танҳо рақам нависед — масалан {example}."
        ),
        "amount_too_small": (
            "Маблағ хеле кам аст. Ҳадди ақал {min_amount} {currency}."
        ),
        "amount_too_large": (
            "Маблағ аз ҳадди имкон зиёд аст. Ҳадди аксар {max_amount} {currency}.\n"
            "Барои маблағи калон ба дастаи Dastyor муроҷиат кунед."
        ),

        "receipt_need_request": (
            "Аввал маблағро интихоб кунед: /pay\n\n"
            "Бе дархости кушода расидро қабул карда наметавонам — ҳар расид бояд "
            "ба як дархости мушаххас тааллуқ дошта бошад."
        ),
        "receipt_unsupported": (
            "Ин навъи файлро хонда наметавонам.\n\n"
            "Қабул мешавад: сурат (JPG, PNG, WEBP) ё PDF.\n"
            "Беҳтарин роҳ — скриншоти расидро ҳамчун сурат фиристед."
        ),
        "receipt_too_large": (
            "Файл хеле калон аст. Ҳадди аксар {max_mb} МБ.\n"
            "Скриншотро хурдтар кунед ё ҳамчун сурат (на файли аслӣ) фиристед."
        ),
        "receipt_no_text": (
            "Дар ин сурат ягон матн наёфт шуд — ба расиди пардохт монанд нест.\n\n"
            "Илтимос, акси равшани расиди интиқоли пул (ё скриншоти бонк)-ро "
            "фиристед. Дархости шумо ҳанӯз кушода аст, метавонед дубора кӯшиш кунед."
        ),
        "receipt_received": (
            "Расид қабул шуд ва ба маъмур барои санҷиш фиристода шуд.\n\n"
            "Рақами дархост: {code}\n"
            "Маблағи дархостшуда: {amount} {currency}\n"
            "{ocr_summary}\n\n"
            "Ҳоло маъмур воридшавии пулро дар ҳисоби воқеӣ месанҷад. Баъд аз он "
            "шумо хабар мегиред. Тавозун ҳоло тағйир наёфт.\n\n"
            "/status — ҳолати дархост"
        ),
        "receipt_read_failed": (
            "Расидро қабул кардам, вале матни онро хонда натавонистам.\n\n"
            "Рақами дархост: {code}\n"
            "Ин дархостро бекор намекунад — маъмур расидро бо чашми худ мебинад. "
            "Агар расид норавшан бошад, метавонед сурати равшантар фиристед."
        ),

        "status_empty": (
            "Шумо ҳоло дархости пардохт надоред.\n/pay — сохтани дархости нав"
        ),
        "status_header": "Дархостҳои пардохти шумо:\n",
        "status_line": "{icon} {code} — {amount} {currency} — {state}{extra}",

        "state_awaiting_receipt": "интизори расид",
        "state_pending": "дар санҷиши маъмур",
        "state_approved": "тасдиқ шуд",
        "state_rejected": "тасдиқ нашуд",
        "state_needs_info": "маълумоти иловагӣ лозим",
        "state_cancelled": "бекор шуд",

        "approved_user": (
            "Пардохти шумо тасдиқ шуд.\n\n"
            "Рақами дархост: {code}\n"
            "Илова шуд: {amount} {currency}\n"
            "Тавозуни нав: {balance} {currency}\n\n"
            "Ташаккур! Акнун метавонед мавод созед."
        ),
        "rejected_user": (
            "Пардохти дархости {code} тасдиқ нашуд.\n\n"
            "Маъмур воридшавии ин маблағро дар ҳисоби қабулкунанда надид. "
            "Тавозуни шумо тағйир наёфт.\n\n"
            "Сабабҳои эҳтимолӣ: пул ҳанӯз нарасидааст, маблағ мувофиқат "
            "намекунад, ё расид ба интиқоли дигар тааллуқ дорад.\n\n"
            "Агар мутмаин бошед, ки пулро фиристодаед, расиди аслиро нигоҳ "
            "доред ва ба дастаи Dastyor муроҷиат кунед."
        ),
        "needs_info_user": (
            "Барои дархости {code} маълумоти иловагӣ лозим аст.\n\n"
            "Маъмур расидро дида истодааст, вале чизе норавшан мондааст. "
            "Лутфан сурати равшантари расид фиристед — бо маблағ, вақт ва "
            "рақами амалиёт.\n\n"
            "Тавозуни шумо ҳанӯз тағйир наёфт ва дархост кушода аст."
        ),

        "temp_error": (
            "Хатои муваққатӣ. Чизе гум нашуд — дархости шумо нигоҳ дошта шуд.\n"
            "Лутфан баъд аз якчанд дақиқа бори дигар кӯшиш кунед."
        ),
        "unlink_confirm": (
            "Ҳисоби {account}-ро аз ин чат ҷудо кунам?\n\n"
            "Баъд аз ҷудошавӣ ин чат тавозунро намебинад ва дархости "
            "пардохт сохта наметавонад. Тавозун ва таърихи пардохтҳои "
            "шумо дар Dastyor бетағйир мемонад.\n\n"
            "Барои тасдиқ нависед: /unlink ҳа"
        ),
        "unlink_done": (
            "Ҳисоб аз ин чат ҷудо шуд.\n\n"
            "Барои пайвасти дубора: барномаи Dastyor -> «Тавозун» -> "
            "«Пур кардани баланс тавассути Telegram»."
        ),
        "unlink_open_requests": (
            "\n\n⚠️ Шумо {count} дархости кушода доред. Онҳо бекор "
            "нашуданд — маъмур онҳоро месанҷад, вале натиҷа ба ин чат "
            "намеояд. Барои гирифтани хабар дубора пайваст шавед."
        ),
        "unlink_admin_revoked": (
            "\n\nҲуқуқи маъмурии шумо низ бекор карда шуд, зеро он ба "
            "ҳамин пайваст асос ёфта буд."
        ),
        "unlink_not_linked": (
            "Ин чат ба ҳеҷ ҳисоб пайваст нест."
        ),

        "login_ask_phone": (
            "Пайвастшавӣ бо рақами телефон.\n\n"
            "Рақами телефонеро, ки бо он дар Dastyor сабти ном кардаед, "
            "фиристед.\n"
            "Масалан: +992900000000"
        ),
        "login_ask_password": (
            "Акнун пароли Dastyor-и худро фиристед.\n\n"
            "⚠️ Паролро фавран пас аз санҷиш нест мекунем.\n"
            "⚠️ Паролро ба ҳеҷ боти дигар нафиристед — ин ягона боти "
            "расмии пардохти Dastyor аст (@{bot})."
        ),
        "login_bad_phone": (
            "Рақами телефон нодуруст аст.\n"
            "Дар шакли +992XXXXXXXXX фиристед."
        ),
        "login_bad_credentials": (
            "Рақами телефон ё парол нодуруст аст.\n\n"
            "Бори дигар кӯшиш кунед: /login"
        ),
        "login_throttled": (
            "Кӯшишҳои зиёд. Як соат интизор шавед ва бори дигар кӯшиш кунед.\n\n"
            "Агар паролро фаромӯш карда бошед, онро дар барномаи Dastyor "
            "барқарор кунед."
        ),
        "login_restart": "Аз нав оғоз кунед: /login",
        "login_delete_failed": (
            "\n\n⚠️ Паролро аз чат нест карда натавонистам. Лутфан "
            "худатон он хабарро нест кунед."
        ),

        "unknown_command": (
            "Ин фармонро намедонам.\n"
            "/pay — пардохт   /balance — тавозун   /status — дархостҳо   /help — кӯмак"
        ),
        "admin_only": "Ин амал танҳо барои маъмурони Dastyor дастрас аст.",


        "account": (
            "👤 {name}\n"
            "🆔 ID Dastyor: {short_id}\n"
            "💰 Тавозун: {balance} {currency}\n"
            "📱 Telegram: пайваст аст\n\n"
            "❗ ID-и худро ба администратор "
            "диҳед, то ӯ тавозуни шуморо пур кунад.\n\n"
            "Ҷудо кардани ҳисоб: /unlink"
        ),
        "history_header": "📋 Таърихи амалиётҳо\n",
        "history_footer": "\n💰 Тавозуни ҳозира: {balance} {currency}",
        "history_empty": (
            "Ҳоло ягон амалиёт нест.\n\n"
            "Вақте ки тавозуни шумо пур мешавад ё мавод месозед, "
            "он дар ин ҷо пайдо мешавад."
        ),
        "history_topup": "➕ {amount} {currency} · {when}",
        "history_charge": "➖ {amount} {currency} · {when}",
        "history_detail": "\n   {detail}",
    },

    "ru": {
        "currency": "сомони",

        # The welcome text is the implementation brief's, verbatim —
        # shown on every /start, linked or not, because the brief asks
        # for it to explain the bot's purpose immediately rather than
        # only on a teacher's very first visit.
        "start_unlinked": (
            "👋 Добро пожаловать в Dastyor Pay!\n\n"
            "Этот бот предназначен для пополнения баланса вашего аккаунта Dastyor.\n\n"
            "Вы можете:\n"
            "• Пополнить баланс.\n"
            "• Отправить чек об оплате.\n"
            "• Проверить статус платежа.\n"
            "• Посмотреть историю операций.\n\n"
            "После отправки чека система проверит его данные и передаст заявку "
            "администратору. Средства будут зачислены только после подтверждения "
            "платежа администратором.\n\n"
            "Сначала подключим ваш аккаунт.\n"
            "Нажмите кнопку «🔑 Войти в аккаунт» — я спрошу номер телефона "
            "и пароль, те же, с которыми вы входите в Dastyor."
        ),
        "start_linked": (
            "👋 Добро пожаловать в Dastyor Pay!\n\n"
            "Этот бот предназначен для пополнения баланса вашего аккаунта Dastyor.\n\n"
            "Вы можете:\n"
            "• Пополнить баланс.\n"
            "• Отправить чек об оплате.\n"
            "• Проверить статус платежа.\n"
            "• Посмотреть историю операций.\n\n"
            "После отправки чека система проверит его данные и передаст заявку "
            "администратору. Средства будут зачислены только после подтверждения "
            "платежа администратором.\n\n"
            "✅ Аккаунт подключён.\n"
            "👤 {account}\n"
            "💰 Баланс: {balance} {currency}"
        ),
        "start_already_linked": (
            "👋 Добро пожаловать в Dastyor Pay!\n\n"
            "Пополняйте баланс Dastyor, отправляйте чеки и отслеживайте "
            "платежи в одном месте.\n\n"
            "💳 Отправьте чек после оплаты.\n"
            "🔎 Система проверит данные и передаст заявку администратору.\n"
            "✅ Средства поступят на баланс после подтверждения оплаты.\n\n"
            "👤 Аккаунт: {account}\n"
            "💰 Баланс: {balance} {currency}"
        ),
        "link_token_invalid": (
            "Ссылка привязки недействительна.\n\n"
            "Откройте приложение Dastyor и нажмите «Пополнить баланс через "
            "Telegram» в разделе «Баланс» — он создаст новую корректную ссылку."
        ),
        "link_token_expired": (
            "Срок действия ссылки истёк.\n\n"
            "Такие ссылки живут недолго — это требование безопасности. Нажмите "
            "«Баланс» -> «Пополнить баланс через Telegram» в приложении ещё раз."
        ),
        "link_token_used": (
            "Эта ссылка уже использована и второй раз не работает.\n\n"
            "Если это были не вы — смените пароль в приложении и сообщите нам. "
            "Для новой привязки получите новую ссылку в приложении."
        ),
        "link_chat_taken": (
            "Этот Telegram-чат уже привязан к другому аккаунту Dastyor.\n\n"
            "Если это ошибка, обратитесь к нам — один чат не может быть привязан "
            "к двум аккаунтам одновременно."
        ),

        "not_linked_short": (
            "Аккаунт не привязан. Приложение Dastyor -> «Баланс» -> "
            "«Пополнить баланс через Telegram».\n"
            "/start — подробнее"
        ),

        "help": (
            "Как пополнить баланс:\n\n"
            "1️⃣  Нажмите «💳 Пополнить баланс» — укажите сумму, я пришлю "
            "реквизиты для перевода\n"
            "2️⃣  Переводите деньги\n"
            "3️⃣  Отправьте фотографию чека — сумма, дата и номер транзакции "
            "должны быть хорошо видны\n"
            "4️⃣  Администратор проверяет поступление и подтверждает оплату\n\n"
            "❗ Баланс пополняется только после того, как "
            "администратор своими глазами увидел поступление на "
            "счёт. Фото чека помогает проверке, но само по себе "
            "её не заменяет — так мы защищены от поддельных чеков.\n\n"
            "🧾 «Проверить статус платежа» покажет, на каком этапе заявка.\n\n"
            "Есть вопрос? Напишите команде Dastyor."
        ),

        "balance": (
            "👤 {account}\n"
            "💰 Баланс: {balance} {currency}\n\n"
            "Один материал стоит {price} {currency}."
        ),

        "pay_not_configured": (
            "Инструкция оплаты пока не настроена в боте.\n\n"
            "Мы не показываем примерные реквизиты — ваши деньги должны уйти "
            "именно туда, куда нужно. Обратитесь к команде Dastyor."
        ),
        "pay_choose_amount": (
            "Сколько вы переводите?\n\n"
            "💰 Сейчас: {balance} {currency}\n"
            "📄 Один материал: {price} {currency}\n\n"
            "Нажмите кнопку ниже 👇\n"
            "Или напишите сумму сами, например: {example}"
        ),
        "pay_instructions": (
            "💳 Оплата\n\n"
            "Переведите {amount} {currency} на:\n"
            "{instructions}\n\n"
            "📸 После перевода отправьте фото чека сюда.\n"
            "✅ Баланс пополнится после проверки оплаты.\n\n"
            "Номер заявки: {code}\n"
            "❗ Ваш ID Dastyor: {account_id}"
        ),
        "amount_invalid": "Не понял сумму. Напишите только число — например {example}.",
        "amount_too_small": "Сумма слишком мала. Минимум {min_amount} {currency}.",
        "amount_too_large": (
            "Сумма больше допустимой. Максимум {max_amount} {currency}.\n"
            "Для крупной суммы обратитесь к команде Dastyor."
        ),

        "receipt_need_request": (
            "Сначала выберите сумму: /pay\n\n"
            "Без открытой заявки квитанцию принять нельзя — каждая квитанция "
            "должна относиться к конкретной заявке."
        ),
        "receipt_unsupported": (
            "Не могу прочитать этот тип файла.\n\n"
            "Принимаются: изображение (JPG, PNG, WEBP) или PDF.\n"
            "Лучший вариант — отправить скриншот квитанции как фото."
        ),
        "receipt_too_large": (
            "Файл слишком большой. Максимум {max_mb} МБ.\n"
            "Уменьшите скриншот или отправьте его как фото, а не как исходный файл."
        ),
        "receipt_no_text": (
            "Это не похоже на чек об оплате.\n"
            "Отправьте настоящий чек — фото или скриншот перевода, где видна "
            "сумма и получатель. Заявка ещё открыта."
        ),
        "receipt_received": (
            "✅ Квитанция получена!\n\n"
            "💰 Вы указали: {amount} {currency}\n"
            "📄 {ocr_summary}\n\n"
            "⏳ Администратор проверяет поступление денег. Баланс пока не изменён.\n\n"
            "📩 После проверки вы получите уведомление.\n"
            "Номер заявки: {code}\n\n"
            "🔎 /status — статус платежа"
        ),
        "receipt_read_failed": (
            "Квитанцию принял, но прочитать её текст не смог.\n\n"
            "Номер заявки: {code}\n"
            "Заявка не отменена — админ посмотрит квитанцию сам. Если она "
            "нечёткая, можете отправить более чёткое фото."
        ),

        "status_empty": "У вас пока нет заявок на оплату.\n/pay — создать заявку",
        "status_header": "Ваши заявки на оплату:\n",
        "status_line": "{icon} {code} — {amount} {currency} — {state}{extra}",

        "state_awaiting_receipt": "ожидает проверки",
        "state_pending": "проверяется",
        "state_approved": "подтверждён",
        "state_rejected": "отклонён",
        "state_needs_info": "нужны дополнительные данные",
        "state_cancelled": "отменена",

        "approved_user": (
            "✅ Оплата подтверждена!\n\n"
            "На ваш баланс Dastyor зачислено: {amount} {currency}.\n\n"
            "Номер операции: {code}\n"
            "Новый баланс: {balance} {currency}\n\n"
            "Спасибо за использование Dastyor!"
        ),
        "rejected_user": (
            "❌ Заявка на пополнение отклонена.\n\n"
            "Номер заявки: {code}\n"
            "Причина: {reason}\n\n"
            "Если вы считаете, что произошла ошибка, обратитесь в поддержку."
        ),
        "needs_info_user": (
            "По заявке {code} нужны дополнительные данные.\n\n"
            "Админ смотрит квитанцию, но что-то осталось неясным. Пришлите, "
            "пожалуйста, более чёткое фото квитанции — с суммой, временем и "
            "номером операции.\n\n"
            "Баланс пока не изменился, заявка остаётся открытой."
        ),

        "temp_error": (
            "Временная ошибка. Ничего не потеряно — ваша заявка сохранена.\n"
            "Попробуйте снова через пару минут."
        ),
        "unlink_confirm": (
            "Отвязать аккаунт {account} от этого чата?\n\n"
            "После отвязки этот чат не будет показывать баланс и не "
            "сможет создавать заявки на оплату. Ваш баланс и история "
            "платежей в Dastyor остаются без изменений.\n\n"
            "Для подтверждения напишите: /unlink да"
        ),
        "unlink_done": (
            "Аккаунт отвязан от этого чата.\n\n"
            "Чтобы привязать снова: приложение Dastyor -> «Баланс» -> "
            "«Пополнить баланс через Telegram»."
        ),
        "unlink_open_requests": (
            "\n\n⚠️ У вас {count} открытых заявок. Они не отменены — "
            "админ их рассмотрит, но результат в этот чат не придёт. "
            "Чтобы получать уведомления, привяжитесь снова."
        ),
        "unlink_admin_revoked": (
            "\n\nПрава администратора тоже сняты — они держались на "
            "этой привязке."
        ),
        "unlink_not_linked": "Этот чат не привязан ни к одному аккаунту.",

        "login_ask_phone": (
            "Привязка по номеру телефона.\n\n"
            "Отправьте номер, на который зарегистрирован ваш аккаунт "
            "Dastyor.\n"
            "Например: +992900000000"
        ),
        "login_ask_password": (
            "Теперь отправьте пароль от Dastyor.\n\n"
            "⚠️ Мы удалим пароль сразу после проверки.\n"
            "⚠️ Никогда не отправляйте пароль другим ботам — официальный "
            "платёжный бот Dastyor только один (@{bot})."
        ),
        "login_bad_phone": (
            "Неверный номер телефона.\n"
            "Отправьте в формате +992XXXXXXXXX"
        ),
        "login_bad_credentials": (
            "Неверный номер телефона или пароль.\n\n"
            "Попробуйте снова: /login"
        ),
        "login_throttled": (
            "Слишком много попыток. Подождите час и попробуйте снова.\n\n"
            "Если забыли пароль — восстановите его в приложении Dastyor."
        ),
        "login_restart": "Начните заново: /login",
        "login_delete_failed": (
            "\n\n⚠️ Не удалось удалить пароль из чата. Пожалуйста, "
            "удалите то сообщение сами."
        ),

        "unknown_command": (
            "Не знаю такую команду.\n"
            "/pay — оплата   /balance — баланс   /status — заявки   /help — помощь"
        ),
        "admin_only": "Это действие доступно только администраторам Dastyor.",


        "account": (
            "👤 {name}\n"
            "🆔 ID Dastyor: {short_id}\n"
            "💰 Баланс: {balance} {currency}\n"
            "📱 Telegram: привязан\n\n"
            "❗ Назовите свой ID администратору — "
            "по нему он пополнит ваш баланс.\n\n"
            "Отвязать аккаунт: /unlink"
        ),
        "history_header": "📋 История операций\n",
        "history_footer": "\n💰 Текущий баланс: {balance} {currency}",
        "history_empty": (
            "Операций пока нет.\n\n"
            "Здесь появятся пополнения баланса и "
            "списания за материалы."
        ),
        "history_topup": "➕ {amount} {currency} · {when}",
        "history_charge": "➖ {amount} {currency} · {when}",
        "history_detail": "\n   {detail}",
    },

    "en": {
        "currency": "somoni",

        "start_unlinked": (
            "Hello! This is the official Dastyor payment bot.\n\n"
            "Your account is not linked yet. Linking is only started from the "
            "app itself — that is what keeps your account safe.\n\n"
            "What to do:\n"
            "1. Open the Dastyor app\n"
            "2. Balance -> \"Top up balance via Telegram\"\n"
            "3. Tap the button — the bot opens and the account gets linked\n\n"
            "The linking link is valid for 5 minutes and works only "
            "once.\n\n"
            "If the link will not open (some networks block t.me), link by "
            "phone number instead: /login"
        ),
        "start_linked": (
            "Your account is linked.\n\n"
            "Account: {account}\n"
            "Current balance: {balance} {currency}\n\n"
            "Commands:\n"
            "/pay — payment instructions and receipt upload\n"
            "/balance — current balance\n"
            "/status — your payment requests\n"
            "/help — how this works"
        ),
        "start_already_linked": (
            "This chat is already linked to account {account}.\n"
            "Balance: {balance} {currency}\n\n"
            "/pay — send a receipt   /status — requests   /help — help"
        ),
        "link_token_invalid": (
            "That linking link is not valid.\n\n"
            "Open the Dastyor app and tap \"Top up balance via Telegram\" on the "
            "Balance screen — it creates a fresh, valid link."
        ),
        "link_token_expired": (
            "The linking link has expired.\n\n"
            "These links are short-lived on purpose. Tap Balance -> \"Top up "
            "balance via Telegram\" in the app again."
        ),
        "link_token_used": (
            "This link has already been used and will not work a second time.\n\n"
            "If that was not you, change your password in the app and tell us. "
            "For a new link, start again from the app."
        ),
        "link_chat_taken": (
            "This Telegram chat is already linked to a different Dastyor "
            "account.\n\nIf that is a mistake, contact us — one chat cannot be "
            "linked to two accounts at once."
        ),

        "not_linked_short": (
            "Your account is not linked. Dastyor app -> Balance -> \"Top up "
            "balance via Telegram\".\n/start — details"
        ),

        "help": (
            "How topping up works:\n\n"
            "1. «➕ Top up balance» — I send you the card number\n"
            "2. Make the transfer\n"
            "3. Tell the administrator your Dastyor ID — it is under "
            "«👤 My account»\n"
            "4. They confirm the money arrived and top up your balance\n\n"
            "❗ A balance is only credited after an administrator has "
            "seen the money arrive in the receiving account. That is what "
            "protects against forged receipts.\n\n"
            "📸 Sending a photo of the receipt is optional.\n\n"
            "Questions? Message the Dastyor team."
        ),

        "balance": (
            "Account: {account}\n"
            "Balance: {balance} {currency}\n\n"
            "Each material costs {price} {currency}.\n"
            "/pay — top up"
        ),

        "pay_not_configured": (
            "Payment instructions have not been configured in the bot yet.\n\n"
            "We will not show approximate account details — your money has to go "
            "to the right place. Please contact the Dastyor team."
        ),
        "pay_choose_amount": (
            "How much are you transferring?\n\n"
            "Current balance: {balance} {currency}\n"
            "Price per material: {price} {currency}\n\n"
            "Tap one of the buttons below, or type the amount as a number "
            "(for example: {example})."
        ),
        "pay_instructions": (
            "Payment request created.\n\n"
            "Request ID: {code}\n"
            "Amount: {amount} {currency}\n\n"
            "{instructions}\n\n"
            "Tell the administrator your Dastyor ID: {account_id}\n"
            "They will check that the money arrived and top up your "
            "balance — I will message you as soon as they do.\n\n"
            "A photo of the receipt is optional. Sending one just makes "
            "you easier to find.\n\n"
            "To cancel: /pay (creates a new request)"
        ),
        "amount_invalid": "I could not read that amount. Type just a number — e.g. {example}.",
        "amount_too_small": "That amount is too small. Minimum {min_amount} {currency}.",
        "amount_too_large": (
            "That amount is above the limit. Maximum {max_amount} {currency}.\n"
            "For a larger amount, contact the Dastyor team."
        ),

        "receipt_need_request": (
            "Pick an amount first: /pay\n\n"
            "A receipt cannot be accepted without an open request — every "
            "receipt has to belong to a specific one."
        ),
        "receipt_unsupported": (
            "I cannot read that file type.\n\n"
            "Accepted: an image (JPG, PNG, WEBP) or a PDF.\n"
            "The easiest option is to send a screenshot of the receipt as a photo."
        ),
        "receipt_too_large": (
            "That file is too large. Maximum {max_mb} MB.\n"
            "Shrink the screenshot, or send it as a photo rather than the "
            "original file."
        ),
        "receipt_no_text": (
            "No text at all was found in that image — it doesn't look like a "
            "payment receipt.\n\n"
            "Please send a clear photo of the receipt (or a screenshot from "
            "your bank). Your request is still open, so you can try again."
        ),
        "receipt_received": (
            "Receipt received and sent to an admin for review.\n\n"
            "Request ID: {code}\n"
            "Requested amount: {amount} {currency}\n"
            "{ocr_summary}\n\n"
            "An admin is now checking that the money arrived in the real "
            "account. You will get a message once that is done. Your balance "
            "has not changed yet.\n\n"
            "/status — request status"
        ),
        "receipt_read_failed": (
            "I accepted the receipt but could not read its text.\n\n"
            "Request ID: {code}\n"
            "The request is still open — an admin will look at the receipt "
            "directly. If it came out blurry, you can send a clearer photo."
        ),

        "status_empty": "You have no payment requests yet.\n/pay — create one",
        "status_header": "Your payment requests:\n",
        "status_line": "{icon} {code} — {amount} {currency} — {state}{extra}",

        "state_awaiting_receipt": "awaiting receipt",
        "state_pending": "under admin review",
        "state_approved": "approved",
        "state_rejected": "not confirmed",
        "state_needs_info": "more information needed",
        "state_cancelled": "cancelled",

        "approved_user": (
            "Your payment has been confirmed.\n\n"
            "Request ID: {code}\n"
            "Credited: {amount} {currency}\n"
            "New balance: {balance} {currency}\n\n"
            "Thank you! You can create materials now."
        ),
        "rejected_user": (
            "Payment for request {code} was not confirmed.\n\n"
            "The admin did not see this amount arrive in the receiving account. "
            "Your balance has not changed.\n\n"
            "Possible reasons: the money has not arrived yet, the amount does "
            "not match, or the receipt belongs to a different transfer.\n\n"
            "If you are sure you sent it, keep the original receipt and contact "
            "the Dastyor team."
        ),
        "needs_info_user": (
            "Request {code} needs more information.\n\n"
            "The admin is looking at your receipt but something is unclear. "
            "Please send a clearer photo showing the amount, the time and the "
            "transaction number.\n\n"
            "Your balance has not changed and the request is still open."
        ),

        "temp_error": (
            "Temporary error. Nothing was lost — your request is saved.\n"
            "Please try again in a couple of minutes."
        ),
        "unlink_confirm": (
            "Disconnect account {account} from this chat?\n\n"
            "Afterwards this chat will not show your balance and cannot "
            "create payment requests. Your Dastyor balance and payment "
            "history are unchanged.\n\n"
            "To confirm, send: /unlink yes"
        ),
        "unlink_done": (
            "Account disconnected from this chat.\n\n"
            "To link again: Dastyor app -> Balance -> \"Top up balance "
            "via Telegram\"."
        ),
        "unlink_open_requests": (
            "\n\n⚠️ You have {count} open request(s). They are not "
            "cancelled — an admin will still review them, but the result "
            "will not reach this chat. Link again to get notified."
        ),
        "unlink_admin_revoked": (
            "\n\nYour administrator rights were revoked too: they rested "
            "on this link."
        ),
        "unlink_not_linked": "This chat is not linked to any account.",

        "login_ask_phone": (
            "Linking by phone number.\n\n"
            "Send the number your Dastyor account is registered to.\n"
            "For example: +992900000000"
        ),
        "login_ask_password": (
            "Now send your Dastyor password.\n\n"
            "⚠️ We delete the password as soon as it is checked.\n"
            "⚠️ Never send your password to any other bot — there is only "
            "one official Dastyor payment bot (@{bot})."
        ),
        "login_bad_phone": (
            "That phone number is not valid.\n"
            "Send it as +992XXXXXXXXX"
        ),
        "login_bad_credentials": (
            "Wrong phone number or password.\n\nTry again: /login"
        ),
        "login_throttled": (
            "Too many attempts. Wait an hour and try again.\n\n"
            "If you forgot the password, reset it in the Dastyor app."
        ),
        "login_restart": "Start again: /login",
        "login_delete_failed": (
            "\n\n⚠️ I could not delete the password from the chat. "
            "Please delete that message yourself."
        ),

        "unknown_command": (
            "I do not know that command.\n"
            "/pay — payment   /balance — balance   /status — requests   /help — help"
        ),
        "admin_only": "This action is only available to Dastyor administrators.",


        "account": (
            "👤 {name}\n"
            "🆔 Dastyor ID: {short_id}\n"
            "💰 Balance: {balance} {currency}\n"
            "📱 Telegram: linked\n\n"
            "❗ Give your ID to the administrator — that is how they "
            "top up your balance.\n\n"
            "Unlink this account: /unlink"
        ),
        "history_header": "📋 Operation history\n",
        "history_footer": "\n💰 Current balance: {balance} {currency}",
        "history_empty": (
            "No operations yet.\n\n"
            "Top-ups and charges for materials will appear here."
        ),
        "history_topup": "➕ {amount} {currency} · {when}",
        "history_charge": "➖ {amount} {currency} · {when}",
        "history_detail": "\n   {detail}",
    },
}


# ---------------------------------------------------------------------
# Administrator-facing strings
# ---------------------------------------------------------------------
#
# A separate catalogue from the teacher-facing one above, in Russian by
# default, because the reviewer is one known person (the owner) rather
# than the Tajik-speaking teachers the rest of the bot serves. The
# language is configurable via TELEGRAM_ADMIN_LANGUAGE.
#
# Note the button labels: the original brief specified Uzbek
# ("Ha, pul tushdi" / "Yo'q, pul tushmadi" / "Qo'shimcha tekshiruv").
# They are Russian here at the owner's later request, since the whole
# admin channel is Russian. The three ACTIONS are unchanged — confirm,
# reject, ask for more — only the wording moved.

ADMIN_MESSAGES: dict[str, dict[str, str]] = {
    "ru": {
        # Field labels and the review header match the implementation
        # brief's admin-notification template verbatim (f_telegram_id is
        # new — see _admin_caption). "Результат проверки" is the pass/
        # mismatch verdict; the OCR engine/confidence detail and the
        # per-warning bullets still follow in summarize_for_admin's
        # block below it, which is a superset of the brief's single
        # "Предупреждения" line, not a replacement for it.
        "review_header": "🔔 Новая оплата",
        "mismatch_short": "⚠️ Сумма не совпадает",
        "f_code": "Номер заявки",
        "f_account": "Аккаунт Dastyor",
        "f_user_id": "ID пользователя Dastyor",
        "f_telegram_id": "Telegram ID",
        "f_requested": "Запрошенная сумма",
        "receipt_header": "— Прочитано с квитанции —",
        "f_amount": "Сумма по OCR",
        "f_currency": "Валюта",
        "f_sender": "Плательщик",
        "f_recipient": "Получатель",
        "f_reference": "Номер транзакции",
        "f_datetime": "Дата платежа",
        "f_status": "Статус",
        "f_validation": "Результат проверки",
        "f_warnings": "Предупреждения",
        "validation_clean": "совпадает, расхождений не найдено",
        "validation_warnings": "есть расхождения — см. предупреждения ниже",
        "no_warnings": "нет",
        "review_footer": "Пожалуйста, проверьте поступление средств перед принятием решения.",
        "duplicate": (
            "🔁 Этот номер операции уже использован в заявке {code}."
        ),
        "ocr_line": "OCR: {engine}, уверенность {confidence}%",
        "warnings_header": "⚠️ Предупреждения:",
        "disclaimer": (
            "❗ OCR не подтверждает оплату. Квитанция может быть "
            "поддельной или отправленной повторно. Поступление денег на "
            "счёт получателя проверьте сами."
        ),
        # Exact labels from the implementation brief for the two primary
        # decisions. The extra two (set a different amount / needs more
        # checking) are not in the brief, kept below them as additional
        # options for the cases a flat yes/no does not fit — see
        # _review_keyboard.
        "btn_approve": "✅ Подтвердить оплату",
        "btn_reject": "❌ Отклонить оплату",
        "btn_set_amount": "💵 Указать другую сумму",
        "btn_more": "🔎 Нужна доп. проверка",
        "ask_amount": (
            'Заявка {code}\nУчитель заявил: {requested} {currency}\n\nСколько поступило на счёт на самом деле?\nНапишите сумму числом — например 25 или 25,50\n\nИменно эта сумма попадёт на баланс учителя.\nДля отмены нажмите «❌ Отмена».'
        ),
        "amount_unreadable": (
            'Не понял сумму. Напишите только число — например 25 или 25,50.\nДля отмены нажмите «❌ Отмена».'
        ),
        "amount_cancelled": "Отменено. Заявка осталась без решения.",
        "amount_applied": (
            '✅ Заявка {code}: зачислено {amount} {currency}.\nБаланс обновлён на сайте.'
        ),
        "ask_rejection_reason": (
            'Заявка {code}\n\nУкажите причину отклонения — учитель увидит этот текст.\n\nДля отмены нажмите «❌ Отмена».'
        ),
        "rejection_applied": '❌ Заявка {code} отклонена. Причина доступна пользователю на сайте.',
        "ack_approved": "Подтверждено, баланс пополнен.",
        "ack_rejected": "Отклонено.",
        "ack_more": "Запрошена дополнительная проверка.",
        "ack_already": "Заявка уже рассмотрена.",
        "ack_not_found": "Заявка не найдена.",
        "ack_duplicate": (
            "Этот номер операции уже подтверждён. Баланс не изменён."
        ),
        "ack_self_approval": (
            "Нельзя подтверждать собственную заявку. Пусть это сделает "
            "другой администратор."
        ),
        "admin_notice_undelivered": (
            "\n\n⚠️ Сообщить ему не удалось — он ещё не открывал этого "
            "бота. Попросите его нажать Start здесь, иначе заявки ему "
            "приходить не будут."
        ),
        "ack_error": "Временная ошибка.",
        "admin_only": "Это действие доступно только администраторам Dastyor.",
        "not_admin_chat": (
            '🔒 Этот бот доступен только администраторам Dastyor. Для пополнения баланса откройте раздел «Баланс» на сайте.'
        ),

        "pending_empty": "✅ Нерассмотренных заявок нет.",
        "pending_header": (
            "Ждут проверки: {count}\n"
            "Сначала самые старые.\n"
        ),
        "pending_line": (
            "{code} — {amount} {currency}\n"
            "   {name} (#{short_id})\n"
            "   ждёт {age}{warn}"
        ),
        "pending_age_hours": "{hours} ч",
        "pending_age_days": "{days} дн",
        "pending_age_fresh": "меньше часа",
        "pending_warn": "  ⚠️ {count}",
        "pending_more": (
            "\nПоказаны первые {shown} из {total}. Разберите эти — "
            "остальные появятся следующими."
        ),
        "pending_stale": (
            "\n⚠️ Самая старая заявка ждёт больше суток. Учитель, скорее "
            "всего, уже перевёл деньги и ждёт."
        ),

        "paycontrol_empty": "(не задано)",
        "paycontrol_current": (
            "💳 Реквизиты для оплаты\n\n"
            "Сейчас учителя видят это:\n"
            "────────────────\n"
            "{current}\n"
            "────────────────\n\n"
            "✏️ Чтобы изменить — просто пришлите новые реквизиты "
            "следующим сообщением.\n\n"
            "Например:\n"
            "Карта: 0000 0000 0000 0000\n"
            "Банк: Алиф\n"
            "Получатель: ИМЯ ФАМИЛИЯ\n\n"
            "Как напишете — так учителя и увидят.\n"
            "Ничего не менять: /cancel"
        ),
        "paycontrol_cancelled": "Оставил как было.",
        "paycontrol_saved": (
            "✅ Готово. Теперь учителя видят это:\n"
            "────────────────\n"
            "{current}\n"
            "────────────────\n\n"
            "Остальные администраторы уведомлены."
        ),
        "paycontrol_changed_notice": (
            "⚠️ Администратор {by} изменил реквизиты для оплаты.\n\n"
            "Было:\n{previous}\n\n"
            "Стало:\n{current}\n\n"
            "Если это не согласовано — проверьте немедленно: именно эти "
            "реквизиты сейчас видят все учителя."
        ),

        "admin_help": (
            '🏠 Используйте кнопки меню. Команды вводить не нужно.\n\n🧾 Проверяйте чеки. 💰 Пополняйте баланс. 📈 Смотрите отчёты.'
        ),
        "admins_header": "Администраторы:",
        "admins_root_tag": "основной (из настроек сервера, снять нельзя)",
        "admins_added_tag": "назначен админом {by}",
        "admin_add_usage": (
            'Нажмите «➕ Добавить администратора» и следуйте подсказкам.'
        ),
        "admin_del_usage": (
            'Нажмите «➖ Снять права» и следуйте подсказкам.'
        ),
        "admin_username_unknown": (
            'Этот @username боту неизвестен. Укажите 6-значный ID аккаунта Dastyor из профиля на сайте.'
        ),
        # The name and ID are echoed back deliberately. A @username is
        # resolved from a stored copy that can be stale, so the admin
        # must be able to see WHO they actually granted, not just that
        # the command succeeded.
        "admin_added": (
            "✅ {name} (#{short_id}) теперь администратор.\n\n"
            "Новые заявки на оплату будут приходить и ему тоже."
        ),
        "admin_added_pending": (
            '✅ {name} (#{short_id}) назначен администратором сайта.\nДля доступа к этому боту необходимо настроить Telegram ID администратора.'
        ),
        "admins_pending_tag": "⏳ ожидает привязки Telegram",
        "admin_removed": "✅ Администратор снят.",
        "admin_already": "Этот пользователь уже администратор.",
        "admin_not_found": (
            "Аккаунт с таким ID не найден. Проверьте 6-значный номер — "
            "он указан в заявке как «Аккаунт Dastyor: #123456»."
        ),
        "admin_not_linked": (
            "У этого аккаунта нет привязанного Telegram.\n\n"
            "Назначение сохранено и включится само при первой привязке."
        ),
        "admin_is_root": (
            'Это основной администратор. Его доступ меняется только в настройках сервера.'
        ),
        "admin_last": (
            "Нельзя снять последнего администратора — тогда заявки "
            "некому было бы подтверждать."
        ),
        "admin_promoted_notice": (
            "Вам выдали права администратора Dastyor.\n\n"
            "Сюда будут приходить заявки на оплату от учителей. По "
            "каждой нужно проверить, действительно ли деньги пришли на "
            "счёт, и нажать кнопку.\n\n"
            "❗ Квитанция не является подтверждением — её можно подделать "
            "или прислать повторно. Подтверждайте только то, что видели "
            "на счёте сами.\n\n"
            "/admins — список администраторов"
        ),
    },
    "tg": {
        "review_header": "🧾 Дархости нави пардохт",
        "f_code": "Рақами дархост",
        "f_account": "Ҳисоби Dastyor",
        "f_user_id": "User ID",
        "f_requested": "Маблағи дархостшуда",
        "receipt_header": "— Аз расид хонда шуд —",
        "f_amount": "Маблағ",
        "f_currency": "Асъор",
        "f_sender": "Фиристанда",
        "f_recipient": "Қабулкунанда",
        "f_reference": "Рақами амалиёт",
        "f_datetime": "Сана/вақт",
        "f_status": "Ҳолат",
        "duplicate": (
            "🔁 Ин рақами амалиёт аллакай дар дархости {code} истифода шудааст."
        ),
        "ocr_line": "OCR: {engine}, эътимод {confidence}%",
        "warnings_header": "⚠️ Огоҳиҳо:",
        "disclaimer": (
            "❗ OCR пардохтро тасдиқ намекунад. Расид метавонад сохта ё "
            "такрорӣ бошад. Воридшавии пулро дар ҳисоби қабулкунанда "
            "худатон санҷед."
        ),
        "btn_approve": "✅ Ҳа, пул омад",
        "btn_reject": "❌ Не, пул наомад",
        "btn_more": "🔎 Санҷиши иловагӣ",
        "ack_approved": "Тасдиқ шуд, тавозун пур шуд.",
        "ack_rejected": "Рад карда шуд.",
        "ack_more": "Маълумоти иловагӣ дархост шуд.",
        "ack_already": "Аллакай баррасӣ шудааст.",
        "ack_not_found": "Дархост ёфт нашуд.",
        "ack_duplicate": (
            "Ин рақами амалиёт аллакай тасдиқ шудааст. Тавозун тағйир наёфт."
        ),
        "ack_error": "Хатои муваққатӣ.",
        "admin_only": "Ин амал танҳо барои маъмурони Dastyor дастрас аст.",
        "not_admin_chat": (
            "Ин боти хизматии Dastyor барои маъмурон аст.\n\n"
            "Агар шумо хоҳед тавозунро пур кунед, барномаи Dastyor-ро "
            "кушоед ва «Пур кардани баланс тавассути Telegram»-ро зер "
            "кунед — он боти лозимиро мекушояд."
        ),
    },
    "en": {
        "review_header": "🧾 New payment request",
        "f_code": "Request ID",
        "f_account": "Dastyor account",
        "f_user_id": "User ID",
        "f_requested": "Requested amount",
        "receipt_header": "— Read from the receipt —",
        "f_amount": "Amount",
        "f_currency": "Currency",
        "f_sender": "Sender",
        "f_recipient": "Recipient",
        "f_reference": "Transaction no.",
        "f_datetime": "Date/time",
        "f_status": "Status",
        "duplicate": "🔁 This transaction number was already used on request {code}.",
        "ocr_line": "OCR: {engine}, confidence {confidence}%",
        "warnings_header": "⚠️ Warnings:",
        "disclaimer": (
            "❗ OCR does not confirm payment. A receipt can be forged or "
            "re-sent. Check the money arrived in the receiving account "
            "yourself."
        ),
        "btn_approve": "✅ Yes, the money arrived",
        "btn_reject": "❌ No, the money did not arrive",
        "btn_more": "🔎 Needs further checking",
        "ack_approved": "Confirmed, balance topped up.",
        "ack_rejected": "Rejected.",
        "ack_more": "Further checking requested.",
        "ack_already": "This request has already been decided.",
        "ack_not_found": "Request not found.",
        "ack_duplicate": (
            "This transaction number is already approved. Balance unchanged."
        ),
        "ack_error": "Temporary error.",
        "admin_only": "This action is only available to Dastyor administrators.",
        "not_admin_chat": (
            "This is the Dastyor service bot for administrators.\n\n"
            "To top up your balance, open the Dastyor app and tap "
            "\"Top up balance via Telegram\" — it opens the right bot."
        ),
    },
}

WARNING_LABELS: dict[str, dict[str, str]] = {
    "ru": {
        "ocr_unavailable": "текст квитанции не прочитан (OCR недоступен)",
        "no_text": "на квитанции не найден текст",
        "amount_missing": "сумма не прочитана",
        "amount_mismatch": "сумма не совпадает с заявкой",
        "currency_unexpected": "другая валюта",
        "sender_missing": "отправитель не указан",
        "recipient_missing": "получатель не прочитан",
        "recipient_mismatch": "получатель не совпадает",
        "reference_missing": "номер операции не найден",
        "reference_duplicate": "этот номер операции уже присылали",
        "date_missing": "дата/время не найдены",
        "low_confidence": "низкая уверенность распознавания",
        "status_not_successful": "на квитанции указан неуспешный статус",
    },
    "tg": {
        "ocr_unavailable": "матни расид хонда нашуд (OCR дастрас нест)",
        "no_text": "дар расид матн ёфт нашуд",
        "amount_missing": "маблағ хонда нашуд",
        "amount_mismatch": "маблағ бо дархост мувофиқат намекунад",
        "currency_unexpected": "асъори дигар",
        "sender_missing": "фиристанда нишон дода нашудааст",
        "recipient_missing": "қабулкунанда хонда нашуд",
        "recipient_mismatch": "қабулкунанда мувофиқат намекунад",
        "reference_missing": "рақами амалиёт ёфт нашуд",
        "reference_duplicate": "ин рақами амалиёт аллакай фиристода шудааст",
        "date_missing": "сана/вақт ёфт нашуд",
        "low_confidence": "эътимоди хониш паст",
        "status_not_successful": "дар расид ҳолати ноком навишта шудааст",
    },
    "en": {
        "ocr_unavailable": "receipt text not read (OCR unavailable)",
        "no_text": "no text found on the receipt",
        "amount_missing": "amount not read",
        "amount_mismatch": "amount does not match the request",
        "currency_unexpected": "unexpected currency",
        "sender_missing": "sender not shown",
        "recipient_missing": "recipient not read",
        "recipient_mismatch": "recipient does not match",
        "reference_missing": "transaction number not found",
        "reference_duplicate": "this transaction number was sent before",
        "date_missing": "date/time not found",
        "low_confidence": "low recognition confidence",
        "status_not_successful": "the receipt shows an unsuccessful status",
    },
}


def admin_t(key: str, language: str | None = None, **kwargs) -> str:
    """Admin catalogue lookup, Russian by default."""
    lang = normalize_lang(language) if language else "ru"
    if lang not in ADMIN_MESSAGES:
        lang = "ru"
    template = ADMIN_MESSAGES[lang].get(key) or ADMIN_MESSAGES["ru"].get(key)
    if template is None:
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def warning_label(code: str, language: str | None = None) -> str:
    lang = normalize_lang(language) if language else "ru"
    if lang not in WARNING_LABELS:
        lang = "ru"
    return WARNING_LABELS[lang].get(code) or WARNING_LABELS["ru"].get(code, code)


STATUS_ICON = {
    "awaiting_receipt": "⏳",
    "pending": "🔍",
    "approved": "✅",
    "rejected": "❌",
    "needs_info": "❓",
    "cancelled": "⚪",
}


def t(key: str, language: str | None = None, **kwargs) -> str:
    """Look a message up, falling back to Tajik then to the raw key.

    Falls back rather than raising because a missing translation must not
    be the reason a teacher's payment flow dies mid-way.
    """
    lang = normalize_lang(language)
    template = MESSAGES.get(lang, {}).get(key) or MESSAGES["tg"].get(key)
    if template is None:
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def state_label(status: str, language: str | None = None) -> str:
    return t(f"state_{status}", language)


def currency(language: str | None = None) -> str:
    return t("currency", language)


# ---------------------------------------------------------------------
# Tappable buttons
# ---------------------------------------------------------------------
#
# Teachers are not developers. "/pay" is invisible to someone who has
# never used a bot: there is nothing on screen telling them it exists,
# and the slash menu is a convention they have no reason to know. A
# persistent reply keyboard puts the same actions where a phone user
# already looks — big labels at the bottom of the chat, one tap each.
#
# The slash commands still work, for the admin and for anyone who
# prefers typing, but nothing in the teacher-facing flow requires them.

BUTTONS: dict[str, dict[str, str]] = {
    "tg": {
        "balance": "💰 Тавозуни ман",
        "topup": "➕ Пур кардани баланс",
        "status": "🧾 Санҷиши ҳолати пардохт",
        "history": "📋 Таърихи амалиётҳо",
        "account": "👤 Ҳисоби ман",
        "help": "❓ Кӯмак",
        "login": "🔑 Ворид шудан",
    },
    # Exact labels from the implementation brief — the teacher side is
    # pinned to this catalogue by `normalize_lang` above, so these are
    # the only labels anyone actually sees today.
    "ru": {
        "balance": "📊 Мой баланс",
        "topup": "💳 Пополнить баланс",
        "status": "🧾 Проверить статус платежа",
        "history": "📜 История платежей",
        "account": "👤 Мой аккаунт",
        "help": "❓ Помощь",
        "login": "🔑 Войти в аккаунт",
    },
    "en": {
        "balance": "💰 My balance",
        "topup": "➕ Top up balance",
        "status": "🧾 Check payment status",
        "history": "📋 Operation history",
        "account": "👤 My account",
        "help": "❓ Help",
        "login": "🔑 Sign in",
    },
}


# The admin's own panel. Same reasoning as the teachers': the person
# reviewing payments should not have to remember command names either.
ADMIN_BUTTONS: dict[str, str] = {
    "credit": "➕ Начислить средства",
    "finduser": "👥 Найти пользователя",
    "history": "📋 История начислений",
    "stats": "📊 Статистика",
    "cancel": "❌ Отмена",
    # Kept from the receipt-review flow, which the brief makes optional
    # rather than removing.
    "pending": "🧾 Заявки с чеками",
    "paycontrol": "💳 Реквизиты",
    "admins": "👤 Администраторы",
    # CRM views added for finance/super tiers - see admin_roles.py and
    # service.has_admin_permission for the gate each one checks.
    "cards": "🏦 Карты",
    "expenses": "💰 Расходы",
    "finance": "📈 Финансы",
    "audit": "📋 Журнал",
}


def admin_button_action(text: str | None) -> str | None:
    if not text:
        return None
    needle = text.strip()
    for action, label in LABELS.items():
        if label == needle:
            return action
    for action, label in ADMIN_BUTTONS.items():
        if label == needle:
            return action
    return None


def button(action: str, language: str | None = None) -> str:
    lang = normalize_lang(language)
    return BUTTONS.get(lang, BUTTONS["tg"]).get(action) \
        or BUTTONS["tg"].get(action, action)


def button_action(text: str | None) -> str | None:
    """Which action a tapped label means, in ANY of the languages.

    Searched across every locale, not just the reader's current one: a
    reply keyboard persists in the chat after a language change, so the
    label still on screen may belong to the previous language. Matching
    only the current one would make those buttons silently dead.
    """
    if not text:
        return None
    needle = text.strip()
    for labels in BUTTONS.values():
        for action, label in labels.items():
            if label == needle:
                return action
    return None


# What the "/" menu in Telegram's UI lists. Registered at startup via
# setMyCommands, so even a teacher who opens that menu sees plain
# descriptions rather than bare command names.
MENU_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "tg": [
        ("balance", "Тавозуни ман"),
        ("pay", "Пур кардани баланс"),
        ("history", "Таърихи амалиётҳо"),
        ("account", "Ҳисоби ман"),
        ("help", "Кӯмак"),
        ("login", "Ворид шудан бо рақами телефон"),
    ],
    "ru": [
        ("balance", "Мой баланс"),
        ("pay", "Пополнить баланс"),
        ("history", "История операций"),
        ("account", "Мой аккаунт"),
        ("help", "Помощь"),
        ("login", "Войти по номеру телефона"),
    ],
    "en": [
        ("balance", "My balance"),
        ("pay", "Top up balance"),
        ("history", "Operation history"),
        ("account", "My account"),
        ("help", "Help"),
        ("login", "Sign in with your phone"),
    ],
}

# The admin bot's own "/" menu. One language, like the rest of that
# channel.
ADMIN_MENU_COMMANDS: list[tuple[str, str]] = [("menu", "🏠 Открыть главное меню")]


# ---------------------------------------------------------------------
# Administrator top-up flow (brief sections 5-7)
# ---------------------------------------------------------------------

TOPUP_TEXTS: dict[str, str] = {
    "ask_user": (
        '➕ Начисление средств\n\nКому начислить? Пришлите:\n• ID аккаунта — 6 цифр, например 123456\n• или номер телефона\n• или часть имени — покажу список\n\nДля отмены нажмите «❌ Отмена».'
    ),
    "user_not_found": (
        'Никого не нашёл по «{query}».\n\nID аккаунта — это 6 цифр, он виден у пользователя в профиле Dastyor. Можно также прислать номер телефона или часть имени.\n\nДля отмены нажмите «❌ Отмена».'
    ),
    "pick_user": (
        'Нашёл несколько. Кого из них?\n\n{options}\nПришлите ID нужного.\nДля отмены нажмите «❌ Отмена».'
    ),
    "pick_user_line": "• {short_id} — {name} (баланс {balance} {currency})",
    "ask_amount": (
        '👤 {name}\n🆔 ID Dastyor: {short_id}\n💰 Текущий баланс: {balance} {currency}\n\nСколько начислить? Напишите сумму числом — например 25 или 25,50\n\nДля отмены нажмите «❌ Отмена».'
    ),
    "amount_not_a_number": (
        'Не понял сумму. Напишите только число — например 25 или 25,50\nДля отмены нажмите «❌ Отмена».'
    ),
    "amount_not_positive": (
        'Сумма должна быть больше нуля.\nДля отмены нажмите «❌ Отмена».'
    ),
    "amount_too_large": (
        'Слишком большая сумма. Максимум за одну операцию — {max_amount} {currency}.\nЕсли нужно больше, сделайте несколько начислений.\nДля отмены нажмите «❌ Отмена».'
    ),
    "ask_note": (
        'Комментарий к операции?\n\nНапример: Оплата через Korti Milli, Ручная корректировка, Бонус.\n\nНажмите «⏭ Без комментария».     Для отмены нажмите «❌ Отмена».'
    ),
    "confirm": (
        "Проверьте перед начислением:\n\n"
        "👤 Пользователь: {name}\n"
        "🆔 ID Dastyor: {short_id}\n"
        "💰 Текущий баланс: {balance_before} {currency}\n"
        "➕ Сумма начисления: {amount} {currency}\n"
        "✅ Баланс после операции: {balance_after} {currency}\n"
        "📝 Комментарий: {note}"
    ),
    "btn_confirm": "✅ Подтвердить начисление",
    "btn_cancel": "❌ Отмена",
    "cancelled": "Операция отменена. Ничего не начислено.",
    "expired": (
        'Эта операция больше не актуальна — бот перезапускался.\nНичего не начислено. Начните заново: «💰 Пополнить баланс»'
    ),
    "applied": (
        "✅ Начислено\n\n"
        "👤 {name} ({short_id})\n"
        "➕ {amount} {currency}\n"
        "💰 Баланс: {balance_before} → {balance_after} {currency}\n"
        "🧾 Операция: {code}\n\n"
        "{notified}"
    ),
    "notified_ok": "Пользователь уведомлён.",
    "notified_failed": (
        "⚠️ Уведомить пользователя не удалось — возможно, он не "
        "привязал Telegram или заблокировал бота. Начисление сохранено."
    ),
    "already_applied": (
        "Эта операция уже выполнена — {code}, {amount} {currency}.\n"
        "Повторно ничего не начислено."
    ),
    "user_gone": "Пользователь не найден. Ничего не начислено.",
    "credit_failed": "Начислить не удалось. Ничего не изменилось.",
    "no_telegram": (
        "\n\n⚠️ У пользователя не привязан Telegram — уведомление он не "
        "получит, но баланс пополнится и будет виден на сайте."
    ),

    # --- find user ---------------------------------------------------
    "ask_find": (
        '👥 Поиск пользователя\n\nПришлите ID аккаунта, номер телефона или часть имени.\nДля отмены нажмите «❌ Отмена».'
    ),
    "found_user": (
        '👤 {name}\n🆔 ID Dastyor: {short_id}\n💰 Баланс: {balance} {currency}\n\nДля пополнения нажмите «💰 Пополнить баланс».'
    ),
    "telegram_linked": "привязан",
    "telegram_not_linked": "не привязан",

    # --- history -----------------------------------------------------
    "history_empty": "Начислений через бота пока нет.",
    "history_header": "📋 Последние начисления:\n",
    "history_line": (
        "{code}  +{amount} {currency}\n"
        "   {name} ({short_id}) · {when}{note}"
    ),
    "history_note": "\n   📝 {note}",

    # --- stats -------------------------------------------------------
    "stats": (
        "📊 Статистика начислений через бота\n\n"
        "Сегодня: {today_count} оп. на {today_amount} {currency}\n"
        "За месяц: {month_count} оп. на {month_amount} {currency}\n"
        "Всего: {total_count} оп. на {total_amount} {currency}\n"
        "Пользователей: {users}"
    ),

    "nothing_to_cancel": "Сейчас нечего отменять.",
}


def topup_t(key: str, **kwargs) -> str:
    """Admin top-up screens. Russian only, like the rest of the admin UI."""
    template = TOPUP_TEXTS.get(key)
    if template is None:
        return key
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


# ---------------------------------------------------------------------
# What a teacher is told when their balance is topped up (section 7)
# ---------------------------------------------------------------------

CREDITED_NOTICE: dict[str, str] = {
    "tg": (
        "✅ Тавозуни Dastyor пур шуд!\n\n"
        "Илова шуд: {amount} {currency}\n"
        "Тавозуни ҳозира: {balance} {currency}\n"
        "Рақами амалиёт: {code}{note}\n\n"
        "Ташаккур барои истифодаи Dastyor!"
    ),
    "ru": (
        "✅ Баланс Dastyor пополнен!\n\n"
        "Начислено: {amount} {currency}\n"
        "Текущий баланс: {balance} {currency}\n"
        "Номер операции: {code}{note}\n\n"
        "Спасибо за использование Dastyor!"
    ),
    "en": (
        "✅ Your Dastyor balance has been topped up!\n\n"
        "Credited: {amount} {currency}\n"
        "Current balance: {balance} {currency}\n"
        "Operation number: {code}{note}\n\n"
        "Thank you for using Dastyor!"
    ),
}

CREDITED_NOTE_LINE: dict[str, str] = {
    "tg": "\nШарҳ: {note}",
    "ru": "\nКомментарий: {note}",
    "en": "\nNote: {note}",
}


def credited_notice(language: str | None, **kwargs) -> str:
    lang = normalize_lang(language)
    return CREDITED_NOTICE.get(lang, CREDITED_NOTICE["tg"]).format(**kwargs)


def credited_note_line(language: str | None, note: str) -> str:
    lang = normalize_lang(language)
    return CREDITED_NOTE_LINE.get(lang, CREDITED_NOTE_LINE["tg"]).format(
        note=note)
