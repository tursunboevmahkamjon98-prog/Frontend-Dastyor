"""The Telegram payment bot: long-polling worker and handlers.

Run it as its own process, next to the API:

    python -m app.telegram.bot

Why polling and not a webhook: the deployment is ``git pull`` plus
``docker compose up``, with no nginx in front and no route to add (see
DEPLOY.md). A webhook would need a public HTTPS path, a TLS certificate
and a reverse-proxy rule — three things that do not exist here — whereas
polling needs only outbound network. The offset is persisted in the
database after every batch, so a restart resumes where it stopped instead
of replaying or skipping.

Why a separate process and not a FastAPI background task: the API runs
``--workers 1`` for reasons its Dockerfile documents at length, and a
poll loop inside it would compete with request handling for that single
worker. A crash in the bot must also not take the API down with it.

Conversation state (which amount a chat is choosing) is held in memory
on purpose — it is worth nothing after a restart, and the teacher simply
taps /pay again. Everything that *is* worth keeping is a row: the
payment request, the receipt, the scan and the audit trail.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import signal
from dataclasses import dataclass

from fastapi import HTTPException

from app.logger import get_logger
from app.security import enforce_user_quota
from app.telegram import admin_crm_bridge, service, topup
from app.telegram.api import (
    ReceiptTooLarge,
    TelegramApiError,
    TelegramClient,
    TelegramTransportError,
    install_token_scrubber,
)
from app.telegram.config import get_telegram_settings
from app.telegram.ocr import (
    ReceiptScan,
    cross_check,
    scan_receipt,
    summarize_for_user,
)
from app.telegram.texts import (
    ADMIN_BUTTONS,
    ADMIN_MENU_COMMANDS,
    MENU_COMMANDS,
    STATUS_ICON,
    admin_button_action,
    admin_t,
    button,
    button_action,
    credited_note_line,
    credited_notice,
    currency,
    fmt_somoni,
    normalize_lang,
    state_label,
    t,
    teacher_lang,
    topup_t,
)

logger = get_logger(__name__)

CB_APPROVE = "pay:ok"
CB_REJECT = "pay:no"
CB_MORE = "pay:more"
CB_SETAMOUNT = "pay:amt"
CB_AMOUNT = "amt"
CB_CREDIT_OK = "tx:ok"
CB_CREDIT_NO = "tx:no"

# Telegram caps a message at 4096 characters; receipts with a long OCR
# dump can exceed that, and an over-long sendMessage fails outright
# rather than truncating.
MAX_MESSAGE_CHARS = 3900


class BotStartupError(RuntimeError):
    """The bot could not start, and the log already says why.

    Separate from the API errors so ``main()`` can exit with a status
    code instead of printing a traceback at an operator who is almost
    certainly looking at a configuration problem.
    """


@dataclass
class ChatState:
    """In-memory, per-chat conversation position.

    ``login_phone`` holds a phone between the two login steps. The
    password is never kept here, or anywhere else — it is verified and
    dropped within the same handler call.
    """
    awaiting_amount: bool = False
    awaiting_login_phone: bool = False
    awaiting_login_password: bool = False
    login_phone: str | None = None
    # Set while an admin is typing the figure that actually
    # arrived, for the request id it names.
    correcting_request_id: str | None = None
    # Set while an admin is typing why they are rejecting a request —
    # the brief wants a reason, and the teacher sees it verbatim.
    rejecting_request_id: str | None = None
    # Set while an admin is composing new payment details.
    awaiting_pay_instructions: bool = False
    # Administrator top-up flow: which step, and what has been
    # gathered so far. None means no top-up in progress.
    topup_stage: str | None = None
    topup_user_id: str | None = None
    topup_dirams: int = 0
    topup_note: str | None = None
    # Set while the admin is being asked to identify a user to look
    # at, which is a read-only lookup rather than a credit.
    awaiting_find_user: bool = False


class PaymentBot:
    """Both halves of the payment flow.

    One process, two Bot API clients:

    * ``client`` is the public, teacher-facing bot. Linking, /pay,
      receipts, notifications.
    * ``admin_client`` is the review bot. The approve/reject buttons
      exist only in its update stream.

    When ``TELEGRAM_ADMIN_BOT_TOKEN`` is unset the two are the same
    object and the behaviour collapses to the original single-bot
    arrangement, so an existing deployment keeps working after it pulls
    this change.
    """

    def __init__(self, client: TelegramClient | None = None,
                 admin_client: TelegramClient | None = None):
        self.settings = get_telegram_settings()
        self.client = client or TelegramClient()

        if admin_client is not None:
            self.admin_client = admin_client
            self.separate_admin_bot = admin_client is not self.client
        elif self.settings.has_separate_admin_bot:
            self.admin_client = TelegramClient(
                self.settings.TELEGRAM_ADMIN_BOT_TOKEN
            )
            self.separate_admin_bot = True
        else:
            self.admin_client = self.client
            self.separate_admin_bot = False

        self.admin_lang = self.settings.TELEGRAM_ADMIN_LANGUAGE
        self._states: dict[int, ChatState] = {}
        # Top-ups that have been previewed but not yet confirmed,
        # keyed by idempotency key. Nothing here has touched a
        # balance, so dropping an entry can only ever cost an admin
        # a retype.
        self._staged_topups: dict[str, dict] = {}
        self._stopping = asyncio.Event()

    # -- small helpers -------------------------------------------------

    # Ceiling on the in-memory conversation table. One small entry per
    # chat that ever wrote, never evicted, is a slow leak on a process
    # meant to run for months — and it is attacker-growable, since
    # anyone can message the public bot. The state is worth nothing
    # (which amount a chat is mid-way through choosing), so the oldest
    # entries are simply dropped; that chat types /pay again.
    MAX_TRACKED_CHATS = 5000

    def _state(self, chat_id: int) -> ChatState:
        state = self._states.get(chat_id)
        if state is None:
            if len(self._states) >= self.MAX_TRACKED_CHATS:
                # dicts preserve insertion order, so this is the
                # least-recently-created entry.
                self._states.pop(next(iter(self._states)), None)
            state = ChatState()
            self._states[chat_id] = state
        return state

    @staticmethod
    def _main_keyboard(language: str | None, linked: bool) -> dict:
        """The persistent button panel at the bottom of the chat.

        What a teacher sees instead of having to know that "/pay"
        exists. ``resize_keyboard`` keeps it one or two rows tall rather
        than taking half the screen, and it is never one-time: the
        buttons have to still be there the next time they open the chat,
        which is the whole point.

        Unlinked chats get a different, shorter panel — offering "top
        up" to somebody with no account attached would just produce an
        error they cannot act on.
        """
        if not linked:
            rows = [
                [{"text": button("login", language)}],
                [{"text": button("help", language)}],
            ]
        else:
            # Exactly the five buttons the implementation brief lists,
            # in its order. "Мой аккаунт" (link status, account name)
            # is still real and still reachable by typing /account —
            # it just is not one of the five the brief asks to show.
            rows = [
                [{"text": button("topup", language)},
                 {"text": button("balance", language)}],
                [{"text": button("status", language)},
                 {"text": button("history", language)}],
                [{"text": button("help", language)}],
            ]
        return {
            "keyboard": rows,
            "resize_keyboard": True,
            "is_persistent": True,
        }

    @staticmethod
    def _admin_keyboard(tier: str = "super") -> dict:
        """The admin's own button panel, filtered by tier.

        Same reasoning as the teachers': whoever reviews payments
        should not have to remember command names either. One language
        only, because the admin channel is Russian by configuration.

        Hiding a row here is UX only - every handler those buttons
        reach re-checks the same permission server-side (see
        service.has_admin_permission / require_permission), so a
        support/readonly admin who somehow sends the raw command text
        still gets refused, not just an invisible button.
        """
        rows = [
            [{"text": ADMIN_BUTTONS["credit"]}],
            [{"text": ADMIN_BUTTONS["finduser"]},
             {"text": ADMIN_BUTTONS["history"]}],
            [{"text": ADMIN_BUTTONS["stats"]},
             {"text": ADMIN_BUTTONS["cancel"]}],
            [{"text": ADMIN_BUTTONS["pending"]},
             {"text": ADMIN_BUTTONS["paycontrol"]}],
        ]
        if tier in ("super", "finance"):
            rows.append([{"text": ADMIN_BUTTONS["cards"]},
                        {"text": ADMIN_BUTTONS["expenses"]}])
        if tier in ("super", "finance", "readonly"):
            rows.append([{"text": ADMIN_BUTTONS["finance"]},
                        {"text": ADMIN_BUTTONS["audit"]}])
        if tier == "super":
            rows.append([{"text": ADMIN_BUTTONS["admins"]}])
        return {
            "keyboard": rows,
            "resize_keyboard": True,
            "is_persistent": True,
        }

    async def _say_with_menu(self, chat_id: int, message: str,
                             language: str | None = None,
                             linked: bool | None = None) -> dict | None:
        """``_say`` with the button panel attached."""
        if linked is None:
            linked = await service.account_for_chat(chat_id) is not None
        return await self._say(
            chat_id, message,
            reply_markup=self._main_keyboard(language, linked),
        )

    async def _say(self, chat_id: int, message: str, *,
                   reply_markup: dict | None = None) -> dict | None:
        """Send a message, swallowing delivery failure.

        A failed notification must not abort the surrounding work: the
        balance has already changed by the time the user is told, and
        raising here would leave the caller unable to distinguish "credit
        failed" from "credit worked but the message did not arrive". The
        failure is logged with the chat id so it can be chased.
        """
        try:
            return await self.client.send_message(
                chat_id, message[:MAX_MESSAGE_CHARS], reply_markup=reply_markup
            )
        except (TelegramApiError, TelegramTransportError) as e:
            logger.error(f"Notification to chat {chat_id} failed: {e}")
            return None

    @staticmethod
    def _amount_keyboard(presets: list[int], lang: str) -> dict:
        rows, row = [], []
        for dirams in presets:
            row.append({
                "text": f"{fmt_somoni(dirams, lang)} {currency(lang)}",
                "callback_data": f"{CB_AMOUNT}:{dirams}",
            })
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        return {"inline_keyboard": rows}

    def _review_keyboard(self, request_id: str) -> dict:
        """The decisions an admin can make about a receipt.

        The top row is the implementation brief's exact pair: one tap
        to approve, one to reject. Approving credits exactly what the
        request itself asked for (``service.approve_payment`` with no
        override) — the teacher's own stated figure, tied to this one
        ``request_id`` and its idempotency key, not a number retyped by
        hand. The OCR block above this keyboard already told the admin
        whether that figure and the receipt agree, so a one-tap approve
        is not approving blind.

        The two extra buttons below are not in the brief. They exist
        for the case a flat yes/no does not fit: the receipt shows a
        different amount than requested, or the picture alone is not
        enough to decide. Keeping them does not change what the top row
        does — it adds a path for the admin to take instead of it.
        """
        return {"inline_keyboard": [
            [{"text": admin_t("btn_approve", self.admin_lang),
              "callback_data": f"{CB_APPROVE}:{request_id}"}],
            [{"text": admin_t("btn_reject", self.admin_lang),
              "callback_data": f"{CB_REJECT}:{request_id}"}],
            [{"text": admin_t("btn_set_amount", self.admin_lang),
              "callback_data": f"{CB_SETAMOUNT}:{request_id}"}],
            [{"text": admin_t("btn_more", self.admin_lang),
              "callback_data": f"{CB_MORE}:{request_id}"}],
        ]}

    # -- commands ------------------------------------------------------

    async def cmd_start(self, chat_id: int, telegram_user_id: int | None,
                        argument: str | None,
                        username: str | None = None) -> None:
        """``/start`` with and without a linking token."""
        if argument:
            result = await service.redeem_link_token(
                argument.strip(), chat_id, telegram_user_id,
                username=username,
            )
            if result.outcome == "linked" and result.account:
                account = result.account
                lang = teacher_lang(account.language)
                await self._say_with_menu(chat_id, t(
                    "start_linked", lang,
                    account=account.label,
                    balance=fmt_somoni(account.balance_dirams, lang),
                    currency=currency(lang),
                ), lang, linked=True)
                if result.became_admin:
                    # An admin grant was waiting for this account to
                    # appear. It is live from this moment, so say what
                    # it means — including that a receipt is not proof.
                    await self._say_admin(
                        chat_id, admin_t("admin_promoted_notice", self.admin_lang)
                    )
                return
            key = {
                "invalid": "link_token_invalid",
                "expired": "link_token_expired",
                "used": "link_token_used",
                "chat_taken": "link_chat_taken",
            }.get(result.outcome, "link_token_invalid")
            # Language is unknown for a failed link — there is no account
            # to read it from — so this is the teacher-pinned language
            # (Russian), same as every other message with no account yet.
            await self._say(chat_id, t(key, teacher_lang()))
            return

        account = await service.account_for_chat(chat_id)
        if account is None:
            # Inline buttons attached directly to this message, not
            # just the reply-keyboard panel below the input box - a
            # brand-new chat with no prior message has nothing on
            # screen to show that panel even exists yet, which is
            # exactly where a first-time user got lost.
            lang = teacher_lang()
            await self._say(
                chat_id, t("start_unlinked", lang),
                reply_markup={"inline_keyboard": [
                    [{"text": button("login", lang), "callback_data": "tlogin"}],
                    [{"text": button("help", lang), "callback_data": "thelp"}],
                ]},
            )
            return
        lang = teacher_lang(account.language)
        await self._say_with_menu(chat_id, t(
            "start_already_linked", lang,
            account=account.label,
            balance=fmt_somoni(account.balance_dirams, lang),
            currency=currency(lang),
        ), lang, linked=True)

    async def cmd_help(self, chat_id: int) -> None:
        account = await service.account_for_chat(chat_id)
        lang = teacher_lang(account.language if account else None)
        await self._say_with_menu(
            chat_id, t("help", lang), lang, linked=account is not None)

    async def cmd_balance(self, chat_id: int) -> None:
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("not_linked_short", teacher_lang()))
            return
        lang = teacher_lang(account.language)
        # Read through rather than trusting the cached row: a top-up
        # approved seconds ago must show here.
        balance = await service.current_balance_dirams(account.user_id)
        await self._say(chat_id, t(
            "balance", lang,
            account=account.label,
            balance=fmt_somoni(balance, lang),
            currency=currency(lang),
            price=fmt_somoni(service.generation_price_dirams(), lang),
        ))

    async def cmd_account(self, chat_id: int) -> None:
        """Who the chat is linked to, and the id to quote to an admin."""
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("not_linked_short", teacher_lang()))
            return
        lang = teacher_lang(account.language)
        balance = await service.current_balance_dirams(account.user_id)
        await self._say(chat_id, t(
            "account", lang,
            name=account.full_name,
            short_id=account.short_id or "\u2014",
            balance=fmt_somoni(balance, lang),
            currency=currency(lang),
        ))

    async def cmd_history(self, chat_id: int) -> None:
        """Every movement on this teacher's balance, newest first.

        Top-ups and charges together: a list of only the credits would
        not add up to the balance printed under it, and the first
        teacher to notice that would be right to distrust both numbers.
        """
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("not_linked_short", teacher_lang()))
            return
        lang = teacher_lang(account.language)
        entries = await topup.user_ledger(account.user_id, limit=10)
        if not entries:
            await self._say(chat_id, t("history_empty", lang))
            return

        lines = [t("history_header", lang)]
        for e in entries:
            amount = fmt_somoni(abs(e.amount_dirams), lang)
            key = "history_charge" if e.is_charge else "history_topup"
            line = t(key, lang, amount=amount, currency=currency(lang),
                     when=e.created_at.strftime("%d.%m %H:%M"))
            detail = e.note or e.material_type
            if detail:
                line += t("history_detail", lang, detail=detail)
            lines.append(line)
        lines.append(t("history_footer", lang,
                       balance=fmt_somoni(
                           await service.current_balance_dirams(
                               account.user_id), lang),
                       currency=currency(lang)))
        await self._say(chat_id, "\n".join(lines))

    async def cmd_pay(self, chat_id: int) -> None:
        self._state(chat_id).awaiting_amount = False
        await self._say(
            chat_id,
            "Balansni to‘ldirish uchun Dastyor web sahifasidagi Balans bo‘limidan foydalaning. "
            "Chek va to‘lov so‘rovlari shu yerda yuboriladi.",
        )

    # Words that count as "yes" on /unlink, in the three languages the
    # bot speaks. Typing the word is the confirmation step: unlinking is
    # not reversible from the chat — only the app can re-establish it —
    # so a single mistyped /unlink must not do it.
    UNLINK_CONFIRM_WORDS = frozenset({
        "ҳа", "ха", "да", "yes", "y", "ok", "ha",
    })

    # Login attempts allowed per chat per hour. Low on purpose: this is
    # a password prompt reachable by anyone who finds the bot, so it is
    # the one surface where guessing is worth throttling hard.
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 3600

    async def cmd_login(self, chat_id: int) -> None:
        """Start phone + password linking.

        Offered because t.me is blocked on some of the networks these
        teachers use, which makes the deep link unusable there. The
        deep link remains the preferred route and is what the app's
        button produces; this is the fallback.
        """
        account = await service.account_for_chat(chat_id)
        if account is not None:
            lang = teacher_lang(account.language)
            await self._say_with_menu(chat_id, t(
                "start_already_linked", lang,
                account=account.label,
                balance=fmt_somoni(account.balance_dirams, lang),
                currency=currency(lang),
            ), lang, linked=True)
            return

        state = self._state(chat_id)
        state.awaiting_login_phone = True
        state.awaiting_login_password = False
        state.login_phone = None
        await self._say(chat_id, t("login_ask_phone", teacher_lang()))

    async def handle_login_phone(self, chat_id: int, body: str) -> None:
        normalized = service.normalize_phone(body)
        state = self._state(chat_id)
        if normalized is None:
            await self._say(chat_id, t("login_bad_phone", teacher_lang()))
            return
        state.login_phone = normalized
        state.awaiting_login_phone = False
        state.awaiting_login_password = True
        await self._say(chat_id, t(
            "login_ask_password", teacher_lang(),
            bot=self.settings.TELEGRAM_BOT_USERNAME,
        ))

    async def handle_login_password(self, chat_id: int, body: str,
                                    message_id: int | None,
                                    telegram_user_id: int | None,
                                    username: str | None) -> None:
        """Verify the password, then scrub it from the chat.

        The deletion happens FIRST, before any slow work and before any
        reply, so the password spends as little time in the chat as
        possible. Everything after that point works from the already-
        captured string, which is never logged or stored.
        """
        state = self._state(chat_id)
        phone = state.login_phone
        state.awaiting_login_password = False
        state.login_phone = None

        deleted = False
        if message_id is not None:
            deleted = await self.client.delete_message(chat_id, message_id)

        if not phone:
            await self._say(chat_id, t("login_restart", teacher_lang()))
            return

        # Throttle on the chat, not the phone: the chat is the thing an
        # attacker controls, and keying on phone would let one bad actor
        # lock a real teacher out of their own login.
        try:
            await enforce_user_quota(
                f"tg:{chat_id}", "telegram_bot_login",
                max_attempts=self.MAX_LOGIN_ATTEMPTS,
                window_seconds=self.LOGIN_WINDOW_SECONDS,
            )
        except HTTPException:
            await self._say(chat_id, t("login_throttled", teacher_lang()))
            return

        result = await service.link_by_password(
            phone, body, chat_id, telegram_user_id, username=username
        )

        if result.outcome == "linked" and result.account:
            account = result.account
            lang = teacher_lang(account.language)
            message = t(
                "start_linked", lang,
                account=account.label,
                balance=fmt_somoni(account.balance_dirams, lang),
                currency=currency(lang),
            )
            if not deleted:
                # Telegram refused the delete (too old, or permissions).
                # The teacher has to be told their password is sitting
                # in the chat; saying nothing would leave it there.
                message += t("login_delete_failed", lang)
            await self._say_with_menu(chat_id, message, lang,
                                      linked=True)
            if result.became_admin:
                await self._say_admin(
                    chat_id, admin_t("admin_promoted_notice", self.admin_lang)
                )
            return

        key = {
            "bad_credentials": "login_bad_credentials",
            "bad_phone": "login_bad_phone",
            "chat_taken": "link_chat_taken",
        }.get(result.outcome, "temp_error")
        await self._say(chat_id, t(key, None))

    async def cmd_unlink(self, chat_id: int, argument: str | None) -> None:
        """Disconnect this chat from its Dastyor account."""
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("unlink_not_linked", teacher_lang()))
            return

        lang = teacher_lang(account.language)
        confirmed = (argument or "").strip().lower() in self.UNLINK_CONFIRM_WORDS
        if not confirmed:
            await self._say(chat_id, t(
                "unlink_confirm", lang, account=account.label
            ))
            return

        result = await service.unlink_account(chat_id=chat_id, actor="teacher")
        if result.outcome != "unlinked":
            await self._say(chat_id, t("unlink_not_linked", lang))
            return

        message = t("unlink_done", lang)
        if result.open_requests:
            message += t("unlink_open_requests", lang,
                         count=result.open_requests)
        if result.admin_revoked:
            message += t("unlink_admin_revoked", lang)
        await self._say_with_menu(chat_id, message, lang, linked=False)

        # Drop the in-memory conversation too, so a half-finished /pay
        # does not survive the disconnect.
        self._states.pop(chat_id, None)

    async def cmd_status(self, chat_id: int) -> None:
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("not_linked_short", teacher_lang()))
            return
        lang = teacher_lang(account.language)
        requests = await service.list_requests(account.user_id)
        if not requests:
            await self._say(chat_id, t("status_empty", lang))
            return

        lines = [t("status_header", lang)]
        for req in requests:
            extra = ""
            if req.status == service.STATUS_APPROVED and req.credited_dirams:
                extra = f" (+{fmt_somoni(req.credited_dirams, lang)})"
            lines.append(t(
                "status_line", lang,
                icon=STATUS_ICON.get(req.status, "•"),
                code=req.public_code,
                amount=fmt_somoni(req.requested_dirams, lang),
                currency=currency(lang),
                state=state_label(req.status, lang),
                extra=extra,
            ))
        await self._say_with_menu(chat_id, "\n".join(lines), lang, linked=True)

    # -- amount selection ---------------------------------------------

    async def handle_amount(self, chat_id: int, dirams: int) -> None:
        await self.cmd_pay(chat_id)

    async def handle_typed_amount(self, chat_id: int, body: str) -> None:
        account = await service.account_for_chat(chat_id)
        lang = teacher_lang(account.language if account else None)
        dirams = service.parse_amount_to_dirams(body)
        if dirams is None:
            presets = self.settings.topup_presets_dirams()
            await self._say(chat_id, t(
                "amount_invalid", lang,
                example=fmt_somoni(presets[0] if presets else 1000, lang),
            ))
            return
        await self.handle_amount(chat_id, dirams)

    # -- receipts ------------------------------------------------------

    async def handle_receipt(self, chat_id: int, message: dict) -> None:
        """Validate, download, scan and file an uploaded receipt."""
        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("not_linked_short", teacher_lang()))
            return
        lang = teacher_lang(account.language)

        request = await service.open_request_for_user(account.user_id)
        if request is None:
            await self._say(chat_id, t("receipt_need_request", lang))
            return

        file_id, mime, declared_size = self._extract_file(message)
        if file_id is None:
            await self._say(chat_id, t("receipt_unsupported", lang))
            return

        max_bytes = self.settings.TELEGRAM_MAX_RECEIPT_BYTES
        if declared_size and declared_size > max_bytes:
            await self._say(chat_id, t(
                "receipt_too_large", lang, max_mb=max_bytes // (1024 * 1024)
            ))
            return

        if mime and mime.lower() not in self.settings.allowed_receipt_mimes:
            await self._say(chat_id, t("receipt_unsupported", lang))
            return

        # Download and scan. Any failure here still leaves the request
        # open and the file_id recorded, so the admin can look at the
        # original even when the pipeline could not read it.
        scan: ReceiptScan
        try:
            info = await self.client.get_file(file_id)
            path = info.get("file_path")
            if not path:
                raise TelegramApiError("getFile", 200, "no file_path in response")
            data = await self.client.download_file(path, max_bytes=max_bytes)
            scan = scan_receipt(data, mime)
        except ReceiptTooLarge:
            await self._say(chat_id, t(
                "receipt_too_large", lang, max_mb=max_bytes // (1024 * 1024)
            ))
            return
        except (TelegramApiError, TelegramTransportError) as e:
            logger.error(f"Receipt download failed for {request.public_code}: {e}")
            await self._say(chat_id, t("temp_error", lang))
            return
        except Exception as e:
            logger.error(
                f"Receipt scan crashed for {request.public_code}: "
                f"{type(e).__name__}: {e}"
            )
            scan = ReceiptScan(engine="scan-error")
            scan.add_warning("no_text")
            data = b""

        # OCR ran to completion and found literally no text at all — not a
        # blurry or oddly-formatted receipt, but an image with nothing to
        # read in it at all (a selfie, a screenshot of something else, any
        # photo sent to the bot while a request happens to be open).
        #
        # This is deliberately narrower than filtering on confidence or a
        # missing field: cross_check's own docstring is explicit that no
        # warning, and no absence of one, should auto-decide anything,
        # because a genuine receipt can still be low-confidence or partly
        # unreadable and still needs a human to look at it. Zero extracted
        # characters is different in kind, not degree — nothing for a human
        # to review either, and asking for a better photo first wastes
        # neither the teacher's time nor the admin's.
        #
        # The engines below are download/decode *failures*, not "ran fine
        # and found nothing" — those still have to reach the admin, since
        # the pipeline not being able to read a file says nothing about
        # whether the file itself is a real receipt.
        _OCR_FAILURE_ENGINES = (
            "unavailable", "pdf-no-text", "scan-error",
            "tesseract-error", "pdf-error", "image-too-large",
        )
        if scan.engine not in _OCR_FAILURE_ENGINES and "no_text" in scan.warnings:
            await self._say(chat_id, t("receipt_no_text", lang))
            return

        # OCR genuinely ran (not a failure engine - see _OCR_FAILURE_ENGINES
        # just above) and still found no amount. That is a real image
        # with nothing receipt-shaped in it (a logo sheet, an unrelated
        # screenshot), not a reason to bother the admin. Scoped to
        # non-failure engines on purpose: when tesseract itself is
        # unavailable (engine="unavailable"), EVERY receipt would have
        # amount_dirams=None regardless of content, and that case is
        # explicitly meant to degrade to "admin reviews the image by
        # eye" (see TELEGRAM_BOT.md) - checking amount here without this
        # exclusion would reject every real receipt the moment OCR
        # infrastructure is missing, which is exactly what happened
        # when this was first tried.
        if scan.engine not in _OCR_FAILURE_ENGINES and scan.amount_dirams is None:
            await self._say(chat_id, t("receipt_no_text", lang))
            return

        cross_check(
            scan,
            requested_dirams=request.requested_dirams,
            expected_recipient=self.settings.TELEGRAM_PAY_RECIPIENT.strip() or None,
        )

        try:
            duplicate_of = await service.attach_receipt(
                request.id, file_id=file_id, mime=mime,
                size_bytes=declared_size or (len(data) if data else None),
                scan=scan,
            )
        except service.RequestNotOpen:
            # The request was decided between the upload and here.
            await self._say(chat_id, t("receipt_need_request", lang))
            return

        if scan.engine in ("unavailable", "pdf-no-text", "scan-error",
                           "tesseract-error", "pdf-error"):
            await self._say(chat_id, t(
                "receipt_read_failed", lang, code=request.public_code
            ))
        else:
            await self._say(chat_id, t(
                "receipt_received", lang,
                code=request.public_code,
                amount=fmt_somoni(request.requested_dirams, lang),
                currency=currency(lang),
                ocr_summary=summarize_for_user(scan, lang),
            ))

        # The bytes go with it: a separate admin bot cannot resend
        # another bot's file_id and has to re-upload.
        await self.notify_admins(request, account, scan, duplicate_of,
                                 file_id, mime, receipt_bytes=data)

    @staticmethod
    def _extract_file(message: dict) -> tuple[str | None, str | None, int | None]:
        """Pick the file out of a message, rejecting everything else.

        ``photo`` is a list of sizes; the last is the largest, which is
        the one worth OCR-ing. A ``document`` carries its own mime type;
        a photo does not, and Telegram has already re-encoded it to JPEG.
        """
        photos = message.get("photo")
        if isinstance(photos, list) and photos:
            largest = photos[-1]
            return largest.get("file_id"), "image/jpeg", largest.get("file_size")

        document = message.get("document")
        if isinstance(document, dict):
            return (
                document.get("file_id"),
                (document.get("mime_type") or "").lower() or None,
                document.get("file_size"),
            )

        return None, None, None

    # -- admin review --------------------------------------------------

    async def _say_admin(self, chat_id: int, message: str, *,
                         reply_markup: dict | None = None,
                         menu: bool = False) -> dict | None:
        """``_say`` on the admin bot. Same swallow-and-log contract.

        ``menu=True`` attaches the admin button panel. Not the default:
        most admin messages carry inline review buttons instead, and
        two keyboards on one message would fight for the same space.
        """
        if menu and reply_markup is None:
            tier = await service.admin_tier_label(chat_id)
            reply_markup = self._admin_keyboard(tier)
        try:
            return await self.admin_client.send_message(
                chat_id, message[:MAX_MESSAGE_CHARS], reply_markup=reply_markup
            )
        except (TelegramApiError, TelegramTransportError) as e:
            logger.error(f"Admin notification to chat {chat_id} failed: {e}")
            return None

    async def notify_admins(self, request, account, scan: ReceiptScan,
                            duplicate_of: str | None, file_id: str,
                            mime: str | None,
                            receipt_bytes: bytes | None = None) -> None:
        """Put the request in front of every configured administrator."""
        # Root admins plus anyone granted from inside the bot.
        admins = sorted(await service.all_admin_ids())
        if not admins:
            logger.error(
                f"Payment request {request.public_code} has no admin to review it: "
                f"TELEGRAM_ADMIN_IDS is empty"
            )
            return

        caption = self._admin_caption(request, account, scan, duplicate_of)
        keyboard = self._review_keyboard(request.id)
        delivered: list[dict] = []

        for admin_id in admins:
            # A file_id is only valid for the bot that received it. When
            # the admin bot is a separate bot it cannot resend the user
            # bot's file_id, so the receipt is re-uploaded from the bytes
            # the pipeline already downloaded. Without this the admin
            # would get "wrong file identifier" and no receipt at all.
            try:
                sent = await self._send_receipt_to_admin(
                    admin_id, file_id, mime, caption, keyboard, receipt_bytes
                )
                delivered.append({
                    "chat_id": admin_id,
                    "message_id": sent.get("message_id"),
                })
            except (TelegramApiError, TelegramTransportError) as e:
                logger.error(
                    f"Could not send {request.public_code} to admin {admin_id}: {e}"
                )
                # Fall back to text: better a reviewable message without
                # the image than no review at all.
                fallback = await self._say_admin(
                    admin_id, caption, reply_markup=keyboard
                )
                if fallback:
                    delivered.append({
                        "chat_id": admin_id,
                        "message_id": fallback.get("message_id"),
                    })

        if delivered:
            await service.record_admin_message(request.id, delivered)

    async def _send_receipt_to_admin(self, admin_id: int, file_id: str,
                                     mime: str | None, caption: str,
                                     keyboard: dict,
                                     receipt_bytes: bytes | None) -> dict:
        is_pdf = mime == "application/pdf"

        if not self.separate_admin_bot:
            # Same bot: the file_id is valid, so resend by reference and
            # avoid re-uploading the bytes.
            if is_pdf:
                return await self.admin_client.send_document(
                    admin_id, file_id, caption=caption, reply_markup=keyboard
                )
            return await self.admin_client.send_photo(
                admin_id, file_id, caption=caption, reply_markup=keyboard
            )

        if not receipt_bytes:
            # Nothing to upload (the download failed earlier). Send the
            # review text so the request is still actionable.
            raise TelegramApiError(
                "sendPhoto", 400, "no receipt bytes to re-upload to the admin bot"
            )

        field = "document" if is_pdf else "photo"
        filename = "receipt.pdf" if is_pdf else "receipt.jpg"
        content_type = mime or ("application/pdf" if is_pdf else "image/jpeg")
        return await self.admin_client.call(
            "sendDocument" if is_pdf else "sendPhoto",
            {
                "chat_id": admin_id,
                "caption": caption,
                # multipart, so the keyboard has to go as a JSON string
                # rather than a nested object.
                "reply_markup": json.dumps(keyboard),
            },
            files={field: (filename, receipt_bytes, content_type)},
        )

    def _admin_caption(self, request, account, scan: ReceiptScan,
                       duplicate_of: str | None) -> str:
        """The review block.

        Deliberately short: just who, how much was claimed, how much the
        receipt shows, and a one-line flag when they disagree. The full
        OCR dump (confidence, engine, raw warnings, Telegram id, uuid)
        used to be printed here too - product feedback was that it
        buried the two numbers an admin actually has to compare under
        detail nobody reads before tapping Confirm, so it is gone from
        this message. None of it was ever load-bearing: approve/reject
        read request_id from the button's callback_data, never from
        anything printed here, and the receipt photo this caption rides
        on is still the thing an admin actually checks the money against.
        """
        lang = self.admin_lang
        money = (
            f"{fmt_somoni(scan.amount_dirams, lang)} {currency(lang)}"
            if scan.amount_dirams is not None else "—"
        )
        lines = [
            admin_t("review_header", lang),
            "",
            f"👤 #{account.short_id or '—'} · {account.full_name}",
            f"💰 {admin_t('f_requested', lang)}: "
            f"{fmt_somoni(request.requested_dirams, lang)} {currency(lang)}",
            f"📄 {admin_t('f_amount', lang)}: {money}",
        ]
        if "amount_mismatch" in scan.warnings:
            lines.append(admin_t("mismatch_short", lang))
        if duplicate_of:
            lines.append(admin_t("duplicate", lang, code=duplicate_of))
        # Telegram caps a photo caption at 1024 characters, unlike a
        # message's 4096 - nowhere near the limit now, but still enforced.
        return "\n".join(lines)[:1024]

    async def handle_callback(self, callback: dict,
                              from_admin_bot: bool = True) -> None:
        """Dispatch an inline-button tap.

        Authorization is the first thing checked and it is checked against
        the configured admin id list, not against anything in the
        callback payload. An unauthorized tap is answered (so the
        tapper's client stops spinning), logged, and does nothing.
        """
        callback_id = callback.get("id")
        data = callback.get("data") or ""
        from_user = callback.get("from") or {}
        telegram_user_id = from_user.get("id")
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")

        # Teacher-facing inline buttons on the unlinked /start greeting.
        # Open to anyone (not an admin action), so this is answered and
        # dispatched before the admin-authorization logic below even
        # looks at the payload - it is a different action namespace
        # entirely, not something that needs to be "allowed through".
        if data in ("tlogin", "thelp") and chat_id is not None:
            await self._ack(callback_id)
            if data == "tlogin":
                await self.cmd_login(chat_id)
            else:
                await self.cmd_help(chat_id)
            return

        if data.startswith(f"{CB_AMOUNT}:"):
            # Amount buttons live in the teacher's chat on the USER bot,
            # so they must be answered there.
            await self._ack(callback_id, admin=False)
            chat = (callback.get("message") or {}).get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is None:
                return
            try:
                dirams = int(data.split(":", 1)[1])
            except (ValueError, IndexError):
                return
            await self.handle_amount(chat_id, dirams)
            return

        # A review button arriving on the public bot. With a separate
        # admin bot these buttons are never sent there, so this can only
        # be someone crafting callback data by hand. Refuse without
        # touching the request, and log it as the probe it is.
        if from_admin_bot is False and self.separate_admin_bot:
            logger.warning(
                f"Review callback {data.rsplit(':', 1)[0]!r} arrived on the "
                f"public bot from telegram user {telegram_user_id}; refusing"
            )
            await self._ack(callback_id, text=admin_t("admin_only", self.admin_lang),
                            alert=True, admin=False)
            return

        # The top-up confirmation. Its payload is an idempotency key
        # rather than a request id, so it is matched by prefix before
        # the review buttons are parsed.
        if data.startswith(f"{CB_CREDIT_OK}:") \
                or data.startswith(f"{CB_CREDIT_NO}:"):
            admin_chat = (callback.get("message") or {}).get("chat") or {}
            admin_chat_id = admin_chat.get("id")
            if admin_chat_id is None:
                await self._ack(callback_id)
                return

            # Checked here and again in do_credit's service call. Being
            # able to tap a button someone else was shown is not
            # authorization to move money.
            if not await service.is_admin(telegram_user_id):
                logger.warning(
                    f"Unauthorized credit action from telegram user "
                    f"{telegram_user_id}"
                )
                await self._ack(callback_id, text=admin_t(
                    "admin_only", self.admin_lang), alert=True)
                return

            key = data.split(":", 2)[2]
            if data.startswith(f"{CB_CREDIT_NO}:"):
                self._staged_topups.pop(key, None)
                self._reset_topup(admin_chat_id)
                await self._ack(callback_id)
                await self._say_admin(admin_chat_id, topup_t("cancelled"),
                                      menu=True)
                return
            await self.do_credit(callback_id, key, admin_chat_id,
                                 telegram_user_id)
            return

        # Callback data is "<prefix>:<request_id>", and a uuid contains no
        # colon, so splitting on the last one separates them unambiguously.
        prefix, _, request_id = data.rpartition(":")

        if prefix not in (CB_APPROVE, CB_REJECT, CB_MORE, CB_SETAMOUNT):
            await self._ack(callback_id)
            return

        # The authorization check, and the only one that matters. Being
        # able to reach the admin bot is not authorization: anyone can
        # find and message it. Only an id in TELEGRAM_ADMIN_IDS acts.
        if not await service.is_admin(telegram_user_id):
            logger.warning(
                f"Unauthorized payment action {prefix} on request {request_id} "
                f"from telegram user {telegram_user_id}"
            )
            await self._ack(callback_id,
                            text=admin_t("admin_only", self.admin_lang),
                            alert=True)
            return

        if prefix == CB_SETAMOUNT:
            await self._ask_correction_amount(
                callback_id, request_id, telegram_user_id)
        elif prefix == CB_APPROVE:
            await self._do_approve(callback_id, request_id, telegram_user_id)
        elif prefix == CB_REJECT:
            await self._ask_rejection_reason(
                callback_id, request_id, telegram_user_id)
        else:
            await self._do_more_info(callback_id, request_id, telegram_user_id)

    async def _ack(self, callback_id: str | None, *, text: str | None = None,
                   alert: bool = False, admin: bool = True) -> None:
        """Answer a callback so the tapper's client stops spinning.

        Defaults to the admin bot: every callback this handles except the
        amount buttons arrives there. A callback id is only answerable by
        the bot that issued it, so answering on the wrong client is a
        silent no-op and the button spins forever.
        """
        if not callback_id:
            return
        client = self.admin_client if admin else self.client
        try:
            await client.answer_callback_query(
                callback_id, text=text, show_alert=alert
            )
        except (TelegramApiError, TelegramTransportError) as e:
            logger.warning(f"answerCallbackQuery failed: {e}")

    async def _clear_buttons(self, request_id: str) -> None:
        """Remove the review message(s) once a decision is recorded.

        Cosmetic only, same as before — the status compare-and-swap in
        service.py is what actually prevents a second decision, and
        nothing here runs until that has already succeeded. This is
        purely about not leaving a decided request's photo+caption
        sitting in the admin chat(s) once it no longer needs a decision.

        Deleting is the goal. TelegramClient.delete_message() already
        swallows its own errors and returns False (an old message past
        Telegram's edit/delete window, the chat blocked the bot since,
        etc.) rather than raising, so a failed delete falls back to just
        dropping the inline keyboard — the old behavior — so a stale
        button can never be tapped either way. Only messages recorded
        for THIS request_id (service.admin_messages) are touched; every
        other user's and every other payment's messages are untouched.
        """
        for message in await service.admin_messages(request_id):
            chat_id, message_id = message.get("chat_id"), message.get("message_id")
            if not chat_id or not message_id:
                continue
            # The review message belongs to the admin bot, so only the
            # admin bot can edit or delete it.
            deleted = await self.admin_client.delete_message(chat_id, message_id)
            if deleted:
                continue
            try:
                await self.admin_client.edit_message_reply_markup(
                    chat_id, message_id, reply_markup=None
                )
            except (TelegramApiError, TelegramTransportError) as e:
                logger.debug(f"Could not clear buttons on {message_id}: {e}")

    async def _do_approve(self, callback_id: str | None, request_id: str,
                          admin_id: int) -> None:
        result = await service.approve_payment(request_id, admin_id)

        if result.outcome == "already_decided":
            await self._ack(callback_id, text=admin_t("ack_already", self.admin_lang), alert=True)
            await self._clear_buttons(request_id)
            return
        if result.outcome == "not_found":
            await self._ack(callback_id, text=admin_t("ack_not_found", self.admin_lang), alert=True)
            return
        if result.outcome == "duplicate_reference":
            await self._ack(
                callback_id,
                text=admin_t("ack_duplicate", self.admin_lang),
                alert=True,
            )
            return
        if result.outcome == "self_approval":
            await self._ack(
                callback_id,
                text=admin_t("ack_self_approval", self.admin_lang),
                alert=True,
            )
            return
        if result.outcome != "applied" or result.request is None:
            await self._ack(callback_id, text=admin_t("ack_error", self.admin_lang), alert=True)
            return

        await self._ack(callback_id, text=admin_t("ack_approved", self.admin_lang))
        await self._clear_buttons(request_id)

        request = result.request
        account = await service.account_for_chat(request.chat_id)
        lang = teacher_lang(account.language if account else None)
        await self._say(request.chat_id, t(
            "approved_user", lang,
            code=request.public_code,
            amount=fmt_somoni(result.credited_dirams, lang),
            balance=fmt_somoni(result.new_balance_dirams, lang),
            currency=currency(lang),
        ))

    async def _ask_correction_amount(self, callback_id: str | None,
                                     request_id: str, admin_id: int) -> None:
        """Ask the admin for the figure that actually arrived.

        The one-tap approve credits what the teacher asked for, which is
        right the vast majority of the time. This is the other case: the
        receipt says something different, or only part of the money
        came. Rather than make the admin approve a number they know is
        wrong, they state the real one.

        It lands in the audited override path — recorded as
        ``approved_with_correction`` with both figures — so a credit
        that did not match the request is never silent.
        """
        request = await service.get_request(request_id)
        if request is None:
            await self._ack(callback_id,
                            text=admin_t("ack_not_found", self.admin_lang),
                            alert=True)
            return
        if request.status not in service.DECIDABLE:
            await self._ack(callback_id,
                            text=admin_t("ack_already", self.admin_lang),
                            alert=True)
            await self._clear_buttons(request_id)
            return

        self._state(admin_id).correcting_request_id = request_id
        await self._ack(callback_id)
        await self._say_admin(admin_id, admin_t(
            "ask_amount", self.admin_lang,
            code=request.public_code,
            requested=fmt_somoni(request.requested_dirams, self.admin_lang),
            currency=currency(self.admin_lang),
        ))

    async def handle_correction_amount(self, admin_id: int, body: str) -> None:
        """The admin typed the amount. Credit exactly that."""
        state = self._state(admin_id)
        request_id = state.correcting_request_id
        lang = self.admin_lang

        if body.strip().lower() in ("/cancel", "отмена", "бекор", "cancel"):
            state.correcting_request_id = None
            await self._say_admin(admin_id, admin_t("amount_cancelled", lang))
            return

        dirams = service.parse_amount_to_dirams(body)
        if dirams is None:
            # Stay in the prompt: a typo should not drop the admin back
            # to a request with no decision on it.
            await self._say_admin(admin_id, admin_t("amount_unreadable", lang))
            return

        state.correcting_request_id = None
        result = await service.approve_payment(
            request_id, admin_id,
            amount_override_dirams=dirams,
            correction_reason=f"amount set by admin from the receipt: "
                              f"{fmt_somoni(dirams, 'en')}",
        )

        if result.outcome == "already_decided":
            await self._say_admin(admin_id, admin_t("ack_already", lang))
            await self._clear_buttons(request_id)
            return
        if result.outcome == "duplicate_reference":
            await self._say_admin(admin_id, admin_t("ack_duplicate", lang))
            return
        if result.outcome == "self_approval":
            await self._say_admin(admin_id, admin_t("ack_self_approval", lang))
            return
        if result.outcome != "applied" or result.request is None:
            await self._say_admin(admin_id, admin_t("ack_not_found", lang))
            return

        await self._clear_buttons(request_id)
        request = result.request
        await self._say_admin(admin_id, admin_t(
            "amount_applied", lang,
            code=request.public_code,
            amount=fmt_somoni(result.credited_dirams, lang),
            currency=currency(lang),
        ))

        account = await service.account_for_chat(request.chat_id)
        user_lang = teacher_lang(account.language if account else None)
        await self._say(request.chat_id, t(
            "approved_user", user_lang,
            code=request.public_code,
            amount=fmt_somoni(result.credited_dirams, user_lang),
            balance=fmt_somoni(result.new_balance_dirams, user_lang),
            currency=currency(user_lang),
        ))

    async def _ask_rejection_reason(self, callback_id: str | None,
                                    request_id: str, admin_id: int) -> None:
        """Ask why, before rejecting — the brief wants a reason the
        teacher actually sees, not a bare "no".

        Mirrors ``_ask_correction_amount``: the request must still be
        decidable (an already-decided one is refused here, not silently
        re-rejected), and the reply is read by the same per-chat text
        router that already watches for a correction amount.
        """
        request = await service.get_request(request_id)
        if request is None:
            await self._ack(callback_id,
                            text=admin_t("ack_not_found", self.admin_lang),
                            alert=True)
            return
        if request.status not in service.DECIDABLE:
            await self._ack(callback_id,
                            text=admin_t("ack_already", self.admin_lang),
                            alert=True)
            await self._clear_buttons(request_id)
            return

        self._state(admin_id).rejecting_request_id = request_id
        await self._ack(callback_id)
        await self._say_admin(admin_id, admin_t(
            "ask_rejection_reason", self.admin_lang, code=request.public_code,
        ))

    async def handle_rejection_reason(self, admin_id: int, body: str) -> None:
        """The admin typed the reason. Reject with exactly that text."""
        state = self._state(admin_id)
        request_id = state.rejecting_request_id
        lang = self.admin_lang

        if body.strip().lower() in ("/cancel", "отмена", "бекор", "cancel"):
            state.rejecting_request_id = None
            await self._say_admin(admin_id, admin_t("amount_cancelled", lang))
            return

        reason = body.strip()[:255]
        state.rejecting_request_id = None
        result = await service.reject_payment(request_id, admin_id, note=reason)
        await self._finish_no_credit(
            None, request_id, result, "rejected_user",
            admin_t("ack_rejected", self.admin_lang), reason=reason,
        )
        if result.outcome == "applied":
            await self._say_admin(admin_id, admin_t(
                "rejection_applied", lang, code=result.request.public_code,
            ))

    async def _do_more_info(self, callback_id: str | None, request_id: str,
                            admin_id: int) -> None:
        result = await service.request_more_info(request_id, admin_id)
        await self._finish_no_credit(callback_id, request_id, result,
                                     "needs_info_user",
                                     admin_t("ack_more", self.admin_lang))

    async def _finish_no_credit(self, callback_id: str | None, request_id: str,
                                result, user_key: str, ack_text: str,
                                **extra: str) -> None:
        if result.outcome == "already_decided":
            await self._ack(callback_id, text=admin_t("ack_already", self.admin_lang), alert=True)
            await self._clear_buttons(request_id)
            return
        if result.outcome != "applied" or result.request is None:
            await self._ack(callback_id, text=admin_t("ack_not_found", self.admin_lang), alert=True)
            return

        await self._ack(callback_id, text=ack_text)
        await self._clear_buttons(request_id)

        request = result.request
        account = await service.account_for_chat(request.chat_id)
        lang = teacher_lang(account.language if account else None)
        await self._say(request.chat_id, t(user_key, lang, code=request.public_code, **extra))

    # -- update dispatch -----------------------------------------------

    async def handle_message(self, message: dict) -> None:
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return
        # Groups are out of scope: a payment conversation in a group chat
        # would show one teacher's request to everyone in it.
        if chat.get("type") not in (None, "private"):
            return

        from_user = message.get("from") or {}
        telegram_user_id = from_user.get("id")

        # The only moment Telegram ever tells us somebody's current
        # @username is when they write to the bot. Keep the copy that
        # /addadmin resolves against fresh; a failure here is logged and
        # ignored, since it is a convenience index and nothing more.
        await service.remember_username(
            telegram_user_id, from_user.get("username")
        )

        if message.get("photo") or message.get("document"):
            await self.cmd_pay(chat_id)
            return

        body = (message.get("text") or "").strip()
        if not body:
            return

        # Single-bot mode: an admin typing a corrected amount shares
        # this handler with the teachers, so the prompt is answered
        # before buttons or commands get a look at the text.
        if self._state(chat_id).correcting_request_id \
                and await service.is_admin(telegram_user_id):
            await self.handle_correction_amount(chat_id, body)
            return

        # A rejection reason being typed, same reasoning as the
        # correction-amount branch above it.
        if self._state(chat_id).rejecting_request_id \
                and await service.is_admin(telegram_user_id):
            await self.handle_rejection_reason(chat_id, body)
            return

        # Likewise for payment details being composed. Without this the
        # card number falls through every branch below and lands on the
        # teacher greeting — which is exactly what happened in testing:
        # the admin sent "1234123412341234" and got "Салом! 👋".
        if self._state(chat_id).awaiting_pay_instructions \
                and await service.is_admin(telegram_user_id):
            await self.apply_pay_instructions(chat_id, telegram_user_id, body)
            return

        # Likewise for a top-up being composed. Checked before the
        # free-text branches below for the same reason: a bare "25" in
        # answer to "how much?" would otherwise be read as a teacher
        # choosing their own top-up amount. Buttons still win, so an
        # admin who taps a teacher button means to leave the flow.
        state = self._state(chat_id)
        if (state.topup_stage or state.awaiting_find_user) \
                and not button_action(body) \
                and await service.is_admin(telegram_user_id):
            await self.route_topup_text(chat_id, telegram_user_id, body)
            return

        # A tapped button arrives as ordinary text equal to its label.
        # Resolved before anything else so the panel works even while a
        # conversation step is open — a teacher who taps "Balance"
        # half-way through choosing an amount means it.
        action = button_action(body)
        if action:
            state = self._state(chat_id)
            state.awaiting_amount = False
            state.awaiting_login_phone = False
            state.awaiting_login_password = False
            state.login_phone = None
            if action == "topup":
                await self.cmd_pay(chat_id)
            elif action == "balance":
                await self.cmd_balance(chat_id)
            elif action == "status":
                await self.cmd_status(chat_id)
            elif action == "account":
                await self.cmd_account(chat_id)
            elif action == "history":
                await self.cmd_history(chat_id)
            elif action == "login":
                await self.cmd_login(chat_id)
            else:
                await self.cmd_help(chat_id)
            return

        if body.startswith("/"):
            command, _, argument = body.partition(" ")
            command = command.split("@", 1)[0].lower()

            # Admin commands on the public bot, for the single-bot
            # deployment where there is no separate review channel. With
            # a separate admin bot they belong there and are refused
            # here, so the public bot never exposes them at all.
            if command in self.ADMIN_COMMANDS:
                if self.separate_admin_bot:
                    await self._say(chat_id, t("unknown_command", teacher_lang()))
                    return
                if not await service.is_admin(telegram_user_id):
                    logger.warning(
                        f"Non-admin telegram user {telegram_user_id} tried "
                        f"{command}"
                    )
                    await self._say(chat_id, t("unknown_command", teacher_lang()))
                    return
                await self.handle_admin_command(chat_id, telegram_user_id, body)
                return

            if command == "/start":
                await self.cmd_start(chat_id, telegram_user_id, argument or None,
                                     username=from_user.get("username"))
            elif command == "/help":
                await self.cmd_help(chat_id)
            elif command == "/balance":
                await self.cmd_balance(chat_id)
            elif command == "/pay":
                await self.cmd_pay(chat_id)
            elif command == "/status":
                await self.cmd_status(chat_id)
            elif command == "/account":
                await self.cmd_account(chat_id)
            elif command == "/history":
                await self.cmd_history(chat_id)
            elif command == "/unlink":
                await self.cmd_unlink(chat_id, argument)
            elif command == "/login":
                await self.cmd_login(chat_id)
            else:
                account = await service.account_for_chat(chat_id)
                lang = teacher_lang(account.language if account else None)
                await self._say(chat_id, t("unknown_command", lang))
            return

        # Login steps are checked before anything else that consumes
        # free text, so a password can never be mistaken for an amount
        # and echoed back into the chat.
        state = self._state(chat_id)
        if state.awaiting_login_password:
            await self.handle_login_password(
                chat_id, body, message.get("message_id"),
                telegram_user_id, from_user.get("username"),
            )
            return
        if state.awaiting_login_phone:
            await self.handle_login_phone(chat_id, body)
            return

        if state.awaiting_amount:
            await self.handle_typed_amount(chat_id, body)
            return

        account = await service.account_for_chat(chat_id)
        if account is None:
            await self._say(chat_id, t("start_unlinked", teacher_lang()))
        else:
            # With the menu attached, not bare. A reply keyboard persists
            # in the chat after the bot's own button set changes, so a
            # teacher can be looking at a label this version no longer
            # recognises — "Мои заявки", say. Answering without a
            # keyboard would leave that stale panel on screen and the
            # same tap would fail forever; answering with one replaces
            # it, so the second tap works.
            await self._say_with_menu(
                chat_id, t("unknown_command",
                           teacher_lang(account.language)),
                teacher_lang(account.language), linked=True)

    async def handle_update(self, update: dict) -> None:
        """One update from the PUBLIC bot, already claimed as unseen."""
        if "callback_query" in update:
            await self.handle_callback(update["callback_query"],
                                       from_admin_bot=not self.separate_admin_bot)
        elif "message" in update:
            await self.handle_message(update["message"])

    async def handle_admin_update(self, update: dict) -> None:
        """One update from the ADMIN bot.

        Only two things can usefully arrive here: a review button tap,
        and a stray message from somebody who found the bot. Teachers
        are never served here — the admin bot has no /pay, no receipts
        and no balance — so a non-admin gets told where to go instead.
        """
        if "callback_query" in update:
            await self.handle_callback(update["callback_query"],
                                       from_admin_bot=True)
            return

        message = update.get("message")
        if not message:
            return
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or chat.get("type") not in (None, "private"):
            return

        from_user = message.get("from") or {}
        telegram_user_id = from_user.get("id")

        if await service.is_admin(telegram_user_id):
            body = (message.get("text") or "").strip()
            # An amount being typed in answer to "Другая сумма" is not
            # a command, and must be read before command dispatch or a
            # bare number would fall through to the help text.
            if self._state(chat_id).correcting_request_id:
                await self.handle_correction_amount(chat_id, body)
                return
            if self._state(chat_id).rejecting_request_id:
                await self.handle_rejection_reason(chat_id, body)
                return
            if self._state(chat_id).awaiting_pay_instructions:
                await self.apply_pay_instructions(
                    chat_id, telegram_user_id, body)
                return
            state = self._state(chat_id)
            # A user id, an amount or a note, as opposed to a command.
            # Button labels and slash commands fall through to the
            # dispatcher so that "Cancel" always works.
            if (state.topup_stage or state.awaiting_find_user) \
                    and not body.startswith("/") \
                    and not admin_button_action(body):
                await self.route_topup_text(chat_id, telegram_user_id, body)
                return
            await self.handle_admin_command(chat_id, telegram_user_id, body)
            return

        logger.info(
            f"Non-admin telegram user {telegram_user_id} messaged the admin bot"
        )
        await self._say_admin(chat_id, admin_t("not_admin_chat", self.admin_lang))

    ADMIN_COMMANDS = ("/pending", "/paycontrol", "/admins", "/addadmin",
                      "/deladmin", "/credit", "/finduser", "/topups",
                      "/stats", "/cancel", "/skip",
                      "/cards", "/expenses", "/finance", "/audit")

    # ---- administrator top-up (brief sections 5-7) -------------------
    #
    # The primary way money reaches a balance. The admin knows the
    # transfer happened — through a bank app, a card, cash — and is
    # recording it. There is no receipt to upload and no "did the money
    # arrive" question to answer, because the person answering it is
    # the one who already knows.
    #
    # Staged operations live in memory keyed by their idempotency key.
    # Losing them to a restart is harmless: nothing has been credited
    # at that point, and the admin is told to start over rather than
    # being shown a confirm button that would do something unknown.

    async def route_topup_text(self, chat_id: int, telegram_user_id: int,
                               body: str) -> None:
        """Send a line of free text to whichever step is waiting."""
        if self._state(chat_id).awaiting_find_user:
            await self.handle_find_user(chat_id, body)
            return
        await self.handle_topup_step(chat_id, telegram_user_id, body)

    def _reset_topup(self, chat_id: int) -> None:
        state = self._state(chat_id)
        state.topup_stage = None
        state.topup_user_id = None
        state.topup_dirams = 0
        state.topup_note = None
        state.awaiting_find_user = False

    async def cmd_credit(self, chat_id: int) -> None:
        self._reset_topup(chat_id)
        self._state(chat_id).topup_stage = "user"
        await self._say_admin(chat_id, topup_t("ask_user"))

    async def cmd_find_user(self, chat_id: int) -> None:
        self._reset_topup(chat_id)
        self._state(chat_id).awaiting_find_user = True
        await self._say_admin(chat_id, topup_t("ask_find"))

    async def cmd_topup_cancel(self, chat_id: int) -> None:
        state = self._state(chat_id)
        busy = (state.topup_stage or state.awaiting_find_user
                or state.awaiting_pay_instructions
                or state.correcting_request_id
                or state.rejecting_request_id)
        self._reset_topup(chat_id)
        state.awaiting_pay_instructions = False
        state.correcting_request_id = None
        state.rejecting_request_id = None
        await self._say_admin(
            chat_id,
            topup_t("cancelled") if busy else topup_t("nothing_to_cancel"),
            menu=True,
        )

    async def _resolve_topup_user(self, chat_id: int, body: str):
        """Turn what the admin typed into exactly one user, or explain.

        An exact id/phone match wins outright. A name match returns a
        list for the admin to choose from — never an automatic pick,
        because crediting the wrong person is the mistake this flow
        must not make easy.
        """
        found = await topup.find_user(body)
        if found is not None:
            return found

        candidates = await topup.search_users(body)
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            lines = "\n".join(
                topup_t("pick_user_line",
                        short_id=c.short_id or "—", name=c.full_name,
                        balance=fmt_somoni(c.balance_dirams, self.admin_lang),
                        currency=currency(self.admin_lang))
                for c in candidates
            )
            await self._say_admin(chat_id, topup_t("pick_user", options=lines))
            return None

        await self._say_admin(chat_id, topup_t("user_not_found", query=body))
        return None

    async def handle_topup_step(self, chat_id: int, telegram_user_id: int,
                                body: str) -> None:
        """One message inside the top-up conversation."""
        state = self._state(chat_id)
        lang = self.admin_lang

        if body.strip().lower() in ("/cancel", "отмена", "cancel"):
            await self.cmd_topup_cancel(chat_id)
            return

        if state.topup_stage == "user":
            found = await self._resolve_topup_user(chat_id, body)
            if found is None:
                return
            state.topup_user_id = found.user_id
            state.topup_stage = "amount"
            await self._say_admin(chat_id, topup_t(
                "ask_amount", name=found.full_name,
                short_id=found.short_id or "—",
                balance=fmt_somoni(found.balance_dirams, lang),
                currency=currency(lang),
            ))
            return

        if state.topup_stage == "amount":
            check = topup.validate_amount(body)
            if not check.ok:
                await self._say_admin(chat_id, topup_t(
                    f"amount_{check.problem}",
                    max_amount=fmt_somoni(
                        self.settings.TELEGRAM_MAX_TOPUP_DIRAMS, lang),
                    currency=currency(lang),
                ))
                return
            state.topup_dirams = check.dirams
            state.topup_stage = "note"
            await self._say_admin(chat_id, topup_t("ask_note"))
            return

        if state.topup_stage == "note":
            note = None if body.strip().lower() in ("/skip", "-") \
                else body.strip()
            state.topup_note = note
            await self._show_topup_confirmation(chat_id)
            return

    async def _show_topup_confirmation(self, chat_id: int) -> None:
        """The preview screen, with the figures read fresh.

        The balance is re-read here rather than reused from the earlier
        step: a generation charge may have landed in between, and an
        admin confirming "35,00 after" should not be looking at a
        number that was true a minute ago.
        """
        state = self._state(chat_id)
        lang = self.admin_lang
        user = await topup.find_user(state.topup_user_id or "")
        if user is None:
            self._reset_topup(chat_id)
            await self._say_admin(chat_id, topup_t("user_gone"), menu=True)
            return

        key = topup.new_idempotency_key()
        self._staged_topups[key] = {
            "chat_id": chat_id,
            "user_id": user.user_id,
            "dirams": state.topup_dirams,
            "note": state.topup_note,
        }
        state.topup_stage = "confirm"

        text_body = topup_t(
            "confirm",
            name=user.full_name, short_id=user.short_id or "—",
            balance_before=fmt_somoni(user.balance_dirams, lang),
            amount=fmt_somoni(state.topup_dirams, lang),
            balance_after=fmt_somoni(
                user.balance_dirams + state.topup_dirams, lang),
            currency=currency(lang),
            note=state.topup_note or "—",
        )
        if user.chat_id is None:
            text_body += topup_t("no_telegram")

        await self._say_admin(chat_id, text_body, reply_markup={
            "inline_keyboard": [
                [{"text": topup_t("btn_confirm"),
                  "callback_data": f"{CB_CREDIT_OK}:{key}"}],
                [{"text": topup_t("btn_cancel"),
                  "callback_data": f"{CB_CREDIT_NO}:{key}"}],
            ],
        })

    async def do_credit(self, callback_id: str | None, key: str,
                        chat_id: int, admin_telegram_id: int) -> None:
        """Apply a staged top-up. Idempotent on ``key``."""
        lang = self.admin_lang
        staged = self._staged_topups.get(key)

        if staged is None:
            # Either the bot restarted, or this is a second tap whose
            # first already consumed the staging entry. Ask the
            # database which, instead of guessing.
            done = await topup.find_by_idempotency_key(key)
            await self._ack(callback_id)
            if done is not None:
                await self._say_admin(chat_id, topup_t(
                    "already_applied", code=done.operation_code,
                    amount=fmt_somoni(done.credited_dirams, lang),
                    currency=currency(lang),
                ))
                return
            await self._say_admin(chat_id, topup_t("expired"),
                                  menu=True)
            return

        # Consumed up front so a rapid double tap finds nothing staged
        # and falls into the branch above, which reads the real answer
        # out of the database.
        self._staged_topups.pop(key, None)
        self._reset_topup(staged["chat_id"])

        result = await topup.credit_user(
            staged["user_id"], staged["dirams"], admin_telegram_id,
            key, note=staged["note"],
        )
        await self._ack(callback_id)

        if result.outcome == "duplicate":
            await self._say_admin(chat_id, topup_t(
                "already_applied", code=result.operation_code,
                amount=fmt_somoni(result.credited_dirams, lang),
                currency=currency(lang),
            ), menu=True)
            return
        if result.outcome == "user_gone":
            await self._say_admin(chat_id, topup_t("user_gone"),
                                  menu=True)
            return
        if result.outcome != "applied":
            await self._say_admin(chat_id, topup_t("credit_failed"),
                                  menu=True)
            return

        user = await topup.find_user(staged["user_id"])
        notified = await self._notify_credited(user, result, staged["note"])

        await self._say_admin(chat_id, topup_t(
            "applied",
            name=user.full_name if user else "—",
            short_id=(user.short_id if user else None) or "—",
            amount=fmt_somoni(result.credited_dirams, lang),
            currency=currency(lang),
            balance_before=fmt_somoni(result.balance_before, lang),
            balance_after=fmt_somoni(result.balance_after, lang),
            code=result.operation_code,
            notified=topup_t("notified_ok") if notified
            else topup_t("notified_failed"),
        ), menu=True)

    # Attempts, and the pause before each retry. Short: an admin is
    # sitting in front of the confirmation screen waiting for the
    # result, so this cannot spend a minute backing off. Long enough to
    # ride out the kind of blip that makes one request fail and the
    # next succeed.
    NOTIFY_ATTEMPTS = 3
    NOTIFY_BACKOFF_SECONDS = (0.0, 1.0, 3.0)

    async def _notify_credited(self, user, result, note) -> bool:
        """Tell the teacher, retrying a transport failure.

        The money has already moved by the time this runs. Raising
        here would leave the caller unable to tell "the credit failed"
        from "the credit worked but the message did not arrive", and
        the second must never look like the first.

        A retry is worth making because the two failures differ in kind.
        A dropped connection or a 5xx is transient and the same message
        will go through in a second. "Forbidden: bot was blocked by the
        user" will never go through, no matter how many times it is
        tried, so it is not retried — the admin is told instead, and the
        top-up is still visible in the teacher's own history.
        """
        if user is None or user.chat_id is None:
            logger.warning(
                f"Credited {result.operation_code} but the user has no linked "
                f"Telegram; no notification sent"
            )
            return False

        lang = teacher_lang(user.language)
        message = credited_notice(
            lang,
            amount=fmt_somoni(result.credited_dirams, lang),
            currency=currency(lang),
            balance=fmt_somoni(result.balance_after, lang),
            code=result.operation_code,
            note=credited_note_line(lang, note) if note else "",
        )
        keyboard = self._main_keyboard(lang, linked=True)

        for attempt in range(self.NOTIFY_ATTEMPTS):
            if attempt:
                await asyncio.sleep(self.NOTIFY_BACKOFF_SECONDS[attempt])
            try:
                await self.client.send_message(
                    user.chat_id, message[:MAX_MESSAGE_CHARS],
                    reply_markup=keyboard,
                )
                if attempt:
                    logger.info(
                        f"Credit notice for {result.operation_code} delivered "
                        f"on attempt {attempt + 1}"
                    )
                return True
            except TelegramTransportError as e:
                logger.warning(
                    f"Credit notice for {result.operation_code} to chat "
                    f"{user.chat_id} failed on attempt {attempt + 1} of "
                    f"{self.NOTIFY_ATTEMPTS}: {e}"
                )
            except TelegramApiError as e:
                # Telegram answered and said no. Retrying will get the
                # same no.
                logger.error(
                    f"Credit {result.operation_code} applied but Telegram "
                    f"refused to deliver the notice to chat {user.chat_id}: "
                    f"{e}"
                )
                return False

        logger.error(
            f"Credit {result.operation_code} applied but notifying chat "
            f"{user.chat_id} failed after {self.NOTIFY_ATTEMPTS} attempts; "
            f"the teacher will still see it in their history"
        )
        return False

    async def cmd_topup_history(self, chat_id: int) -> None:
        lang = self.admin_lang
        entries = await topup.topup_history(limit=12)
        if not entries:
            await self._say_admin(chat_id, topup_t("history_empty"), menu=True)
            return
        lines = [topup_t("history_header")]
        for e in entries:
            lines.append(topup_t(
                "history_line", code=e.operation_code or "—",
                amount=fmt_somoni(e.amount_dirams, lang),
                currency=currency(lang), name=e.full_name,
                short_id=e.short_id or "—",
                when=e.created_at.strftime("%d.%m %H:%M"),
                note=topup_t("history_note", note=e.note) if e.note else "",
            ))
        await self._say_admin(chat_id, "\n\n".join(lines), menu=True)

    async def cmd_topup_stats(self, chat_id: int) -> None:
        lang = self.admin_lang
        s = await topup.topup_stats()
        await self._say_admin(chat_id, topup_t(
            "stats",
            today_count=s.today_count,
            today_amount=fmt_somoni(s.today_dirams, lang),
            month_count=s.month_count,
            month_amount=fmt_somoni(s.month_dirams, lang),
            total_count=s.total_count,
            total_amount=fmt_somoni(s.total_dirams, lang),
            users=s.distinct_users, currency=currency(lang),
        ), menu=True)

    async def handle_find_user(self, chat_id: int, body: str) -> None:
        lang = self.admin_lang
        self._state(chat_id).awaiting_find_user = False
        found = await self._resolve_topup_user(chat_id, body)
        if found is None:
            return
        await self._say_admin(chat_id, topup_t(
            "found_user", name=found.full_name,
            short_id=found.short_id or "—",
            balance=fmt_somoni(found.balance_dirams, lang),
            currency=currency(lang),
            telegram=topup_t("telegram_linked") if found.chat_id
            else topup_t("telegram_not_linked"),
        ), menu=True)

    async def cmd_paycontrol(self, chat_id: int, telegram_user_id: int,
                             argument: str) -> None:
        """Show or replace the payment details teachers see in /pay.

        Kept in the database rather than the env file so the person who
        owns the card can change it, without a server edit and a
        restart.

        Because this decides where every teacher's money goes, a change
        is announced to every other admin. An attacker who reached one
        admin account could otherwise point all incoming payments at
        their own card and nobody would be told.
        """
        lang = self.admin_lang
        current = await service.get_pay_instructions()

        if not argument.strip():
            # Two steps, not one. Card details are several lines, and
            # expecting them typed after the command on the same
            # message is the kind of format you have to be told twice.
            # Show what is live, then just take the next message.
            self._state(chat_id).awaiting_pay_instructions = True
            await self._say_admin(chat_id, admin_t(
                "paycontrol_current", lang,
                current=current.strip() or admin_t("paycontrol_empty", lang),
            ), menu=True)
            return

        await self.apply_pay_instructions(chat_id, telegram_user_id, argument)

    async def apply_pay_instructions(self, chat_id: int,
                                     telegram_user_id: int,
                                     argument: str) -> None:
        """Store new payment details and tell the other admins."""
        lang = self.admin_lang
        self._state(chat_id).awaiting_pay_instructions = False

        if argument.strip().lower() in ("/cancel", "отмена", "бекор", "cancel"):
            await self._say_admin(chat_id, admin_t("paycontrol_cancelled", lang))
            return

        previous = await service.set_pay_instructions(
            argument.strip(), telegram_user_id
        )
        await self._say_admin(chat_id, admin_t(
            "paycontrol_saved", lang, current=argument.strip()
        ))

        # Tell the other admins. Not the one who made the change —
        # they already know.
        for other in sorted(await service.all_admin_ids()):
            if other == telegram_user_id:
                continue
            await self._say_admin(other, admin_t(
                "paycontrol_changed_notice", lang,
                by=telegram_user_id,
                previous=(previous or "").strip()
                or admin_t("paycontrol_empty", lang),
                current=argument.strip(),
            ))

    # How many requests /pending re-sends with buttons in one go. Each
    # is its own message, and Telegram throttles a burst to one chat, so
    # a long queue is paged rather than fired all at once.
    PENDING_PAGE = 8

    def _format_age(self, hours: float) -> str:
        lang = self.admin_lang
        if hours < 1:
            return admin_t("pending_age_fresh", lang)
        if hours < 48:
            return admin_t("pending_age_hours", lang, hours=int(hours))
        return admin_t("pending_age_days", lang, days=int(hours // 24))

    async def cmd_pending(self, chat_id: int) -> None:
        """Every request still awaiting a decision.

        The safety net under the notification path: a review message can
        fail to arrive, and without this the request would sit in the
        database with nothing pointing at it. Each one is re-sent with
        its buttons, so the queue is not just visible but actionable.
        """
        lang = self.admin_lang
        total = await service.count_pending_reviews()
        if total == 0:
            await self._say_admin(chat_id, admin_t("pending_empty", lang),
                                  menu=True)
            return

        reviews = await service.list_pending_reviews(limit=self.PENDING_PAGE)

        header = [admin_t("pending_header", lang, count=total)]
        for r in reviews:
            warn = (admin_t("pending_warn", lang, count=len(r.ocr_warnings))
                    if r.ocr_warnings else "")
            header.append(admin_t(
                "pending_line", lang,
                code=r.public_code,
                amount=fmt_somoni(r.requested_dirams, lang),
                currency=currency(lang),
                name=r.full_name,
                short_id=r.short_id or "—",
                age=self._format_age(r.age_hours()),
                warn=warn,
            ))
        if total > len(reviews):
            header.append(admin_t("pending_more", lang,
                                  shown=len(reviews), total=total))
        if reviews and reviews[0].age_hours() > 24:
            header.append(admin_t("pending_stale", lang))

        await self._say_admin(chat_id, "\n\n".join(header))

        # Then each request on its own, with the decision buttons, so
        # the admin can act straight from the list.
        for r in reviews:
            keyboard = self._review_keyboard(r.id)
            caption = admin_t(
                "pending_line", lang,
                code=r.public_code,
                amount=fmt_somoni(r.requested_dirams, lang),
                currency=currency(lang),
                name=r.full_name,
                short_id=r.short_id or "—",
                age=self._format_age(r.age_hours()),
                warn="",
            )
            sent = None
            receipt_bytes = None
            if r.receipt_path:
                receipt_root = Path(__file__).resolve().parents[2] / "uploads" / "receipts"
                receipt_file = receipt_root / Path(r.receipt_path).name
                try:
                    if receipt_file.is_file() and receipt_file.stat().st_size <= self.settings.TELEGRAM_MAX_RECEIPT_BYTES:
                        receipt_bytes = receipt_file.read_bytes()
                except OSError as e:
                    logger.warning(f"Could not read stored receipt for {r.public_code}: {e}")
            if r.receipt_file_id and not self.separate_admin_bot:
                try:
                    if r.receipt_mime == "application/pdf":
                        sent = await self.admin_client.send_document(
                            chat_id, r.receipt_file_id,
                            caption=caption, reply_markup=keyboard,
                        )
                    else:
                        sent = await self.admin_client.send_photo(
                            chat_id, r.receipt_file_id,
                            caption=caption, reply_markup=keyboard,
                        )
                except (TelegramApiError, TelegramTransportError) as e:
                    logger.debug(f"Could not resend receipt for {r.public_code}: {e}")
            elif receipt_bytes:
                try:
                    sent = await self._send_receipt_to_admin(
                        chat_id, r.receipt_file_id or "", r.receipt_mime,
                        caption, keyboard, receipt_bytes,
                    )
                except (TelegramApiError, TelegramTransportError) as e:
                    logger.debug(f"Could not re-upload receipt for {r.public_code}: {e}")
            if sent is None:
                # No receipt to show, or a separate admin bot that cannot
                # resend another bot's file_id. The buttons still work.
                await self._say_admin(chat_id, caption, reply_markup=keyboard)

    async def handle_admin_command(self, chat_id: int, telegram_user_id: int,
                                   body: str) -> None:
        """Administrator-only commands.

        The caller has already established that ``telegram_user_id`` is
        an admin. Promotion is the sensitive one: it hands someone the
        ability to move money, so every grant and revoke is written to
        the same append-only audit log as the payments themselves.
        """
        lang = self.admin_lang
        # A tapped admin button arrives as plain text; map it onto
        # the command it stands for.
        tapped = admin_button_action(body)
        if tapped:
            body = f"/{tapped}"
        command, _, argument = body.partition(" ")
        command = command.split("@", 1)[0].lower()
        argument = argument.strip()

        if command == "/credit":
            await self.cmd_credit(chat_id)
            return

        if command == "/finduser":
            await self.cmd_find_user(chat_id)
            return

        if command in ("/topups", "/history"):
            await self.cmd_topup_history(chat_id)
            return

        if command == "/stats":
            await self.cmd_topup_stats(chat_id)
            return

        if command == "/cancel":
            await self.cmd_topup_cancel(chat_id)
            return

        if command == "/skip":
            # Only meaningful as the answer to "any comment?".
            if self._state(chat_id).topup_stage == "note":
                await self.route_topup_text(chat_id, telegram_user_id, "/skip")
            else:
                await self._say_admin(chat_id, topup_t("nothing_to_cancel"),
                                      menu=True)
            return

        if command == "/pending":
            await self.cmd_pending(chat_id)
            return

        if command == "/paycontrol":
            await self.cmd_paycontrol(chat_id, telegram_user_id, argument)
            return

        if command == "/admins":
            entries = await service.list_admins()
            lines = [admin_t("admins_header", lang), ""]
            for e in entries:
                who = f"#{e.short_id} {e.full_name}" if e.short_id else str(
                    e.telegram_user_id)
                if e.is_root:
                    tag = admin_t("admins_root_tag", lang)
                elif e.pending:
                    tag = admin_t("admins_pending_tag", lang)
                else:
                    tag = admin_t("admins_added_tag", lang,
                                  by=e.added_by_telegram_id or "—")
                lines.append(f"• {who}\n   {tag}")
            lines.append("")
            lines.append(admin_t("admin_help", lang))
            await self._say_admin(chat_id, "\n".join(lines))
            return

        if command == "/addadmin":
            if not await service.has_admin_permission(telegram_user_id, "admins.manage"):
                await self._say_admin(chat_id, "⛔ Только супер-администратор может назначать админов.")
                return
            if not argument:
                await self._say_admin(chat_id, admin_t("admin_add_usage", lang)
                                      + "\nЧтобы указать уровень: /addadmin <id> <super|finance|support|readonly>")
                return
            # Optional trailing tier word: "/addadmin 123456 finance".
            ident_part, _, tier_part = argument.partition(" ")
            tier_part = tier_part.strip().lower() or None
            result = await service.add_admin_by_short_id(
                ident_part, telegram_user_id, tier=tier_part
            )
            if result.outcome not in ("added", "added_pending"):
                await self._say_admin(chat_id, admin_t({
                    "already": "admin_already",
                    "username_unknown": "admin_username_unknown",
                }.get(result.outcome, "admin_not_found"), lang))
                return

            entry = result.entry
            confirmation = admin_t(
                "admin_added" if result.outcome == "added"
                else "admin_added_pending",
                lang,
                name=entry.full_name or "—", short_id=entry.short_id or "—",
            )

            delivered = True
            if entry.telegram_user_id is not None:
                # Tell the new admin, in their own chat, what they now
                # hold — including that a receipt is not proof. Someone
                # handed a money-moving button without that sentence is
                # exactly who approves on the strength of a screenshot.
                delivered = await self._say_admin(
                    entry.telegram_user_id,
                    admin_t("admin_promoted_notice", lang),
                ) is not None

            if not delivered and self.separate_admin_bot:
                # Telegram forbids a bot from opening a conversation. A
                # person promoted on the REVIEW bot who has never
                # pressed Start there cannot be messaged by it at all,
                # so they would silently never receive a single review.
                # The granting admin has to know that.
                confirmation += admin_t("admin_notice_undelivered", lang)

            await self._say_admin(chat_id, confirmation)
            # A pending grant has no chat to notify yet; cmd_start sends
            # the same notice at link time.
            return

        if command == "/cards":
            await self._say_admin(chat_id, await admin_crm_bridge.cards_text(telegram_user_id))
            return

        if command == "/expenses":
            await self._say_admin(chat_id, await admin_crm_bridge.expenses_text(telegram_user_id))
            return

        if command == "/finance":
            await self._say_admin(chat_id, await admin_crm_bridge.finance_report_text(telegram_user_id))
            return

        if command == "/audit":
            await self._say_admin(chat_id, await admin_crm_bridge.audit_log_text(telegram_user_id))
            return

        if command == "/deladmin":
            if not await service.has_admin_permission(telegram_user_id, "admins.manage"):
                await self._say_admin(chat_id, "⛔ Только супер-администратор может снимать админов.")
                return
            if not argument:
                await self._say_admin(chat_id, admin_t("admin_del_usage", lang))
                return
            result = await service.remove_admin(argument, telegram_user_id)
            key = {
                "removed": "admin_removed",
                "is_root": "admin_is_root",
                "last_admin": "admin_last",
                "not_found": "admin_not_found",
            }.get(result.outcome, "admin_not_found")
            await self._say_admin(chat_id, admin_t(key, lang))
            return

        await self._say_admin(chat_id, admin_t("admin_help", lang),
                              menu=True)

    # -- the loop ------------------------------------------------------

    def request_stop(self) -> None:
        self._stopping.set()

    async def _verify_token(self, client: TelegramClient, label: str,
                            expected_username: str | None = None) -> str:
        """getMe, with the failures an operator actually hits spelled out.

        Called before any polling so a bad token fails here with an
        explanation rather than as an unexplained 401 on every poll. A
        revoked token is the single most likely startup problem —
        @BotFather revoke invalidates it immediately.
        """
        try:
            me = await client.get_me()
        except TelegramApiError as e:
            if e.status in (401, 404):
                logger.error(
                    f"Telegram rejected the {label} bot token (HTTP "
                    f"{e.status}). It is wrong, or it was revoked in "
                    "@BotFather - revoking invalidates the old token at "
                    "once. Put the current token in backend/.env.telegram "
                    "and restart. Nothing was started."
                )
            else:
                logger.error(f"getMe failed for the {label} bot: {e}")
            raise BotStartupError(str(e)) from None
        except TelegramTransportError as e:
            logger.error(
                f"Could not reach api.telegram.org for the {label} bot: {e}"
            )
            raise BotStartupError(str(e)) from None

        username = me.get("username") or ""
        if expected_username and username.lower() != expected_username.lower():
            # The app builds its deep link from the configured username.
            # If it disagrees with the token's real bot, every link the
            # app hands out opens the wrong chat — and the symptom would
            # be "linking silently never works", which is miserable to
            # debug. Say it loudly at startup instead.
            logger.error(
                f"TELEGRAM_BOT_USERNAME is {expected_username!r} but this "
                f"token belongs to @{username}. Every deep link the app "
                "builds would open the wrong bot. Fix it and restart."
            )
            raise BotStartupError("bot username does not match the token")
        return username

    async def run(self) -> None:
        try:
            user_name = await self._verify_token(
                self.client, "user",
                expected_username=self.settings.TELEGRAM_BOT_USERNAME or None,
            )
            admin_name = user_name
            if self.separate_admin_bot:
                admin_name = await self._verify_token(self.admin_client, "admin")
                if admin_name.lower() == user_name.lower():
                    # Two tokens for one bot: both loops would poll the
                    # same queue and Telegram 409s whichever asks second,
                    # which reads as the bot randomly ignoring people.
                    raise BotStartupError(
                        "the admin token belongs to the same bot as the user "
                        "token; use a second bot or leave "
                        "TELEGRAM_ADMIN_BOT_TOKEN empty"
                    )
        except BotStartupError:
            await self._close_clients()
            raise

        if self.separate_admin_bot:
            logger.info(
                f"Telegram payment bot online: users @{user_name}, "
                f"reviews @{admin_name} (config: {self.settings.redacted()})"
            )
        else:
            logger.warning(
                f"Telegram payment bot online as @{user_name} with NO separate "
                f"admin bot — reviews go to the admin ids through the public "
                f"bot. Set TELEGRAM_ADMIN_BOT_TOKEN to split them. "
                f"(config: {self.settings.redacted()})"
            )

        try:
            pruned = await service.prune_processed_updates()
            if pruned:
                logger.info(f"Pruned {pruned} old processed-update ids")
        except Exception as e:
            logger.warning(f"Processed-update prune skipped: {e}")

        await self._backfill_usernames()
        await self._register_menu()

        loops = [self._poll("user", self.client, self.handle_update)]
        if self.separate_admin_bot:
            loops.append(
                self._poll("admin", self.admin_client, self.handle_admin_update)
            )

        # gather, not a task group: if one loop dies the other should
        # keep serving until the process is stopped deliberately.
        await asyncio.gather(*loops, return_exceptions=True)

        logger.info("Telegram payment bot stopping")
        await self._close_clients()

    async def _register_menu(self) -> None:
        """Fill Telegram's "/" menu with readable descriptions.

        A second, independent way in for anyone who taps the menu
        button instead of the keyboard panel — and the only thing that
        makes a bare command list self-explanatory rather than a set of
        words to guess at.

        Tajik is registered as the default, with ru and en attached to
        their language codes so Telegram picks by the reader's own
        interface language.
        """
        default = MENU_COMMANDS["tg"]
        await self.client.set_my_commands(default)
        for code in ("ru", "en"):
            await self.client.set_my_commands(MENU_COMMANDS[code], code)

        # The admin bot gets its own list. Only when it is a separate
        # bot: in single-bot mode these commands would show up in every
        # teacher's menu, and a teacher tapping "Начислить средства"
        # would get a refusal they cannot act on.
        if self.separate_admin_bot:
            try:
                await self.admin_client.set_my_commands(ADMIN_MENU_COMMANDS)
            except (TelegramApiError, TelegramTransportError) as e:
                logger.warning(f"Could not register admin commands: {e}")

    async def _backfill_usernames(self) -> None:
        """Fill in @usernames for accounts that linked before we stored them.

        ``getChat`` returns a private chat's current username, and the
        bot is allowed to call it for any chat it already knows — which
        every linked account is. Without this, somebody who linked
        yesterday stays unfindable by ``/addadmin @name`` until they
        happen to write to the bot again, and an admin waiting to
        promote them has no way to make that happen.

        Best-effort and bounded: a failure is logged and the account is
        simply retried on the next start.
        """
        try:
            pending = await service.accounts_missing_username()
        except Exception as e:
            logger.warning(f"Username backfill skipped: {e}")
            return
        if not pending:
            return

        filled = 0
        for chat_id, telegram_user_id in pending:
            try:
                chat = await self.client.get_chat(chat_id)
            except (TelegramApiError, TelegramTransportError) as e:
                logger.debug(f"getChat failed for {chat_id}: {e}")
                continue
            username = chat.get("username")
            if not username:
                # The account simply has no @username set. Nothing to
                # store; /addadmin by id still works for them.
                continue
            await service.remember_username(telegram_user_id, username)
            filled += 1

        if filled:
            logger.info(
                f"Backfilled {filled} Telegram username(s) for linked accounts"
            )

    async def _close_clients(self) -> None:
        await self.client.aclose()
        if self.separate_admin_bot:
            await self.admin_client.aclose()

    async def _poll(self, bot: str, client: TelegramClient, handler) -> None:
        """One long-poll loop. Two of these run concurrently.

        ``bot`` namespaces both the dedupe key and the stored offset.
        Update ids are allocated per bot, so sharing either across the
        two would make one bot's update look like a replay of the
        other's and silently drop it.
        """
        offset = await service.get_poll_offset(bot)
        logger.info(f"[{bot}] resuming long-poll from offset {offset}")

        while not self._stopping.is_set():
            try:
                updates = await client.get_updates(
                    offset, self.settings.TELEGRAM_POLL_TIMEOUT_SECONDS
                )
            except TelegramApiError as e:
                delay = e.retry_after or self.settings.TELEGRAM_POLL_ERROR_BACKOFF_SECONDS
                logger.warning(
                    f"[{bot}] getUpdates rejected ({e}); backing off {delay:.1f}s"
                )
                await self._sleep(delay)
                continue
            except TelegramTransportError as e:
                logger.warning(f"[{bot}] getUpdates unreachable ({e}); backing off")
                await self._sleep(self.settings.TELEGRAM_POLL_ERROR_BACKOFF_SECONDS)
                continue

            for update in updates:
                update_id = update.get("update_id")
                if update_id is None:
                    continue
                # Advance the offset even if handling fails: a single
                # poisonous update must not wedge the queue forever. It is
                # logged, and nothing it was supposed to change has
                # changed, so the teacher can retry.
                offset = max(offset, update_id + 1)
                try:
                    if not await service.claim_update(bot, update_id):
                        logger.info(
                            f"[{bot}] skipping already-processed update {update_id}"
                        )
                        continue
                    await handler(update)
                except Exception as e:
                    logger.error(
                        f"[{bot}] update {update_id} failed: {type(e).__name__}: {e}"
                    )

            if updates:
                try:
                    await service.set_poll_offset(bot, offset)
                except Exception as e:
                    # Losing the offset means at-least-once redelivery,
                    # which claim_update already makes safe.
                    logger.warning(
                        f"[{bot}] could not persist poll offset {offset}: {e}"
                    )

    async def _sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stopping.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass


async def main() -> int:
    install_token_scrubber()
    settings = get_telegram_settings()

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set. Put it in backend/.env.telegram "
            "(gitignored) or the process environment, then restart."
        )
        return 2
    if not settings.TELEGRAM_BOT_USERNAME:
        logger.error(
            "TELEGRAM_BOT_USERNAME is not set; the app cannot build a deep link "
            "without it."
        )
        return 2
    if not await service.all_admin_ids():
        logger.error(
            "No Telegram reviewers are configured. Set TELEGRAM_ADMIN_IDS or "
            "grant at least one administrator in the database."
        )
        return 2
    if not settings.TELEGRAM_PAY_INSTRUCTIONS.strip():
        logger.warning(
            "TELEGRAM_PAY_INSTRUCTIONS is empty: /pay will tell teachers the "
            "bot is not configured yet instead of inventing account details."
        )

    bot = PaymentBot()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, bot.request_stop)
        except NotImplementedError:
            # Windows: no add_signal_handler. KeyboardInterrupt below.
            pass

    try:
        await bot.run()
    except BotStartupError:
        # run() has already logged the specific cause and closed the
        # client; a traceback here would bury it.
        return 3
    except KeyboardInterrupt:
        bot.request_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
