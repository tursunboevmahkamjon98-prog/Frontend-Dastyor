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


from app.logger import get_logger
from app.telegram import admin_crm_bridge, service, topup
from app.telegram import admin_ui as ui
from app.telegram.api import (TelegramApiError, TelegramClient, TelegramTransportError, install_token_scrubber)
from app.telegram.config import get_telegram_settings
from app.telegram.texts import (ADMIN_BUTTONS, ADMIN_MENU_COMMANDS, admin_button_action, admin_t, currency, fmt_somoni, topup_t)

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
    admin_action: str | None = None
    admin_target: str | None = None
    admin_tier: str | None = None


class PaymentBot:
    """One Telegram bot for administrator commands and web payment reviews."""

    def __init__(self, client: TelegramClient | None = None):
        self.settings = get_telegram_settings()
        self.admin_client = client or TelegramClient()
        self.admin_lang = "ru"
        self._states: dict[int, ChatState] = {}
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
    def _admin_keyboard(tier: str = "super") -> dict:
        return ui.shortcuts(tier)


    def _review_keyboard(self, request_id: str) -> dict:
        return ui.review(request_id)

    # -- commands ------------------------------------------------------


    # Words that count as "yes" on /unlink, in the three languages the
    # bot speaks. Typing the word is the confirmation step: unlinking is
    # not reversible from the chat — only the app can re-establish it —
    # so a single mistyped /unlink must not do it.

    # Login attempts allowed per chat per hour. Low on purpose: this is
    # a password prompt reachable by anyone who finds the bot, so it is
    # the one surface where guessing is worth throttling hard.


    # -- amount selection ---------------------------------------------


    # -- receipts ------------------------------------------------------


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
        elif reply_markup is None:
            reply_markup = ui.context(self._state(chat_id))
        try:
            return await self.admin_client.send_message(
                chat_id, message[:MAX_MESSAGE_CHARS], reply_markup=reply_markup
            )
        except (TelegramApiError, TelegramTransportError) as e:
            logger.error(f"Admin notification to chat {chat_id} failed: {e}")
            return None


    async def _send_receipt_to_admin(self, admin_id: int, file_id: str,
                                     mime: str | None, caption: str,
                                     keyboard: dict, receipt_bytes: bytes | None) -> dict:
        is_pdf = mime == "application/pdf"
        if receipt_bytes:
            field = "document" if is_pdf else "photo"
            return await self.admin_client.call(
                "sendDocument" if is_pdf else "sendPhoto",
                {"chat_id": admin_id, "caption": caption, "reply_markup": json.dumps(keyboard)},
                files={field: ("receipt.pdf" if is_pdf else "receipt.jpg", receipt_bytes,
                               mime or "image/jpeg")},
            )
        if file_id:
            send = self.admin_client.send_document if is_pdf else self.admin_client.send_photo
            return await send(admin_id, file_id, caption=caption, reply_markup=keyboard)
        raise TelegramApiError("sendPhoto", 400, "receipt is unavailable")


    async def handle_callback(self, callback: dict) -> None:
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

        chat = message.get("chat") or {}
        if (chat.get("type") != "private" or chat_id != telegram_user_id
                or not await service.is_admin(telegram_user_id)):
            await self._ack(callback_id, text=admin_t("admin_only", self.admin_lang), alert=True)
            return

        if data.startswith("ui:"):
            await self._ack(callback_id)
            await self.handle_ui(telegram_user_id, data[3:])
            return
        if data.startswith("pay:") and not await self._allowed(telegram_user_id, "payments.review"):
            await self._ack(callback_id, text="Недостаточно прав.", alert=True)
            return
        if data.startswith("tx:") and not await self._allowed(telegram_user_id, "balance.manage"):
            await self._ack(callback_id, text="Недостаточно прав.", alert=True)
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
            staged = self._staged_topups.get(key)
            if staged and staged["chat_id"] != telegram_user_id:
                await self._ack(callback_id, text="Это подтверждение другого администратора.", alert=True)
                return
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
                   alert: bool = False) -> None:
        if not callback_id:
            return
        try:
            await self.admin_client.answer_callback_query(callback_id, text=text, show_alert=alert)
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

        await self._say_admin(admin_id, admin_t(
            "amount_applied", self.admin_lang,
            code=result.request.public_code,
            amount=fmt_somoni(result.credited_dirams, self.admin_lang),
            currency=currency(self.admin_lang),
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

    async def handle_update(self, update: dict) -> None:
        await self.handle_admin_update(update)

    async def handle_admin_update(self, update: dict) -> None:
        if "callback_query" in update:
            await self.handle_callback(update["callback_query"])
            return
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        sender_id = (message.get("from") or {}).get("id")
        if chat.get("type") != "private" or chat_id is None or sender_id != chat_id:
            return
        if not await service.is_admin(sender_id):
            await self.admin_client.send_message(chat_id, "🔒 Этот бот доступен только администраторам Dastyor.")
            return
        body = (message.get("text") or "").strip()
        tapped = admin_button_action(body)
        if tapped or body.startswith("/"):
            command = tapped or body.partition(" ")[0].split("@", 1)[0].lstrip("/").lower()
            if command not in ("skip", "cancel"):
                self._reset_dialog(chat_id)
            await self.handle_admin_command(chat_id, sender_id, body)
            return
        state = self._state(chat_id)
        if state.admin_action in ("add", "remove"):
            if not await service.has_admin_permission(sender_id, "admins.manage"):
                self._reset_dialog(chat_id)
                await self._say_admin(chat_id, "⛔ Недостаточно прав для управления администраторами.")
                return
            if not body or len(body) > 64 or len(body.split()) != 1:
                await self._say_admin(chat_id, "Пришлите один ID аккаунта Dastyor или известный боту @username.")
                return
            state.admin_target = body
            if state.admin_action == "add":
                state.admin_action = "role"
                rows = [[ui.button("grant:"+key, label)] for key,label in ui.TIERS.items()]
                rows.extend(ui.navigation()["inline_keyboard"])
                await self._say_admin(chat_id, "👤 Аккаунт: " + body + "\nВыберите уровень доступа:", reply_markup={"inline_keyboard": rows})
            else:
                state.admin_action = "remove_confirm"
                await self._say_admin(chat_id, "Снять права администратора у аккаунта " + body + "?", reply_markup={"inline_keyboard": [[ui.button("remove_confirm", "✅ Снять права")], *ui.navigation()["inline_keyboard"]]})
            return
        if state.correcting_request_id:
            if await self._allowed(sender_id, "payments.review"):
                await self.handle_correction_amount(chat_id, body)
        elif state.rejecting_request_id:
            if await self._allowed(sender_id, "payments.review"):
                await self.handle_rejection_reason(chat_id, body)
        elif state.awaiting_pay_instructions:
            if await self._allowed(sender_id, "cards.manage"):
                await self.apply_pay_instructions(chat_id, sender_id, body)
        elif state.topup_stage or state.awaiting_find_user:
            if state.awaiting_find_user or await self._allowed(sender_id, "balance.manage"):
                await self.route_topup_text(chat_id, sender_id, body)
        else:
            await self.cmd_menu(chat_id)

    async def _allowed(self, admin_id: int, permission: str) -> bool:
        if await service.has_admin_permission(admin_id, permission):
            return True
        await self._say_admin(admin_id, "⛔ Недостаточно прав для этого действия.")
        return False

    def _reset_dialog(self, chat_id: int) -> None:
        self._states[chat_id] = ChatState()
        for key in [key for key, value in self._staged_topups.items() if value["chat_id"] == chat_id]:
            self._staged_topups.pop(key, None)

    async def cmd_menu(self, chat_id: int) -> None:
        self._reset_dialog(chat_id)
        tier = await service.admin_tier_label(chat_id)
        await self._say_admin(chat_id, ui.MENU_TEXT, reply_markup=ui.menu(tier))

    async def handle_ui(self, chat_id: int, action: str) -> None:
        state = self._state(chat_id)
        if action.startswith("amount:"):
            if state.topup_stage != "amount":
                await self._say_admin(chat_id, "Эта кнопка устарела. Начните пополнение заново.")
                return
            amount = action.split(":", 1)[1]
            if amount in ("5", "10", "20", "50", "100") and await self._allowed(chat_id, "balance.manage"):
                await self.route_topup_text(chat_id, chat_id, amount)
            return
        if action == "edit_requisites":
            if await self._allowed(chat_id, "cards.manage"):
                self._reset_dialog(chat_id)
                self._state(chat_id).awaiting_pay_instructions = True
                await self._say_admin(chat_id, "✏️ Пришлите новые реквизиты одним сообщением: банк, номер счёта и имя получателя.")
            return
        if action.startswith("grant:"):
            tier = action.split(":", 1)[1]
            if state.admin_action == "role" and tier in ui.TIERS and await self._allowed(chat_id, "admins.manage"):
                state.admin_tier = tier
                state.admin_action = "grant_confirm"
                await self._say_admin(chat_id, f"Назначить администратора?\n👤 {state.admin_target}\n{ui.TIERS[tier]}", reply_markup={"inline_keyboard": [[ui.button("grant_confirm", "✅ Назначить")], *ui.navigation()["inline_keyboard"]]})
            return
        if action in ("grant_confirm", "remove_confirm"):
            if state.admin_action != action or not state.admin_target:
                await self._say_admin(chat_id, "Это подтверждение устарело. Откройте раздел заново.")
                return
            if not await self._allowed(chat_id, "admins.manage"):
                return
            command = "/addadmin " + state.admin_target + " " + (state.admin_tier or "support") if action == "grant_confirm" else "/deladmin " + state.admin_target
            self._reset_dialog(chat_id)
            await self.handle_admin_command(chat_id, chat_id, command)
            return
        if action in ui.LABELS:
            if action not in ("skip", "cancel"):
                self._reset_dialog(chat_id)
            await self.handle_admin_command(chat_id, chat_id, "/" + action)

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
        self._reset_dialog(chat_id)
        await self._say_admin(chat_id, "✅ Действие отменено. Незавершённые изменения не сохранены.", menu=True)
        await self.cmd_menu(chat_id)

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

        await self._say_admin(chat_id, topup_t(
            "applied",
            name=user.full_name if user else "—",
            short_id=(user.short_id if user else None) or "—",
            amount=fmt_somoni(result.credited_dirams, lang),
            currency=currency(lang),
            balance_before=fmt_somoni(result.balance_before, lang),
            balance_after=fmt_somoni(result.balance_after, lang),
            code=result.operation_code,
            notified="Баланс обновлён на сайте.",
        ), menu=True)

    # Attempts, and the pause before each retry. Short: an admin is
    # sitting in front of the confirmation screen waiting for the
    # result, so this cannot spend a minute backing off. Long enough to
    # ride out the kind of blip that makes one request fail and the
    # next succeed.


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
        found = await self._resolve_topup_user(chat_id, body)
        if found is None:
            return
        self._state(chat_id).awaiting_find_user = False
        await self._say_admin(chat_id, topup_t(
            "found_user", name=found.full_name,
            short_id=found.short_id or "—",
            balance=fmt_somoni(found.balance_dirams, lang),
            currency=currency(lang),
            telegram=topup_t("telegram_linked") if found.chat_id
            else topup_t("telegram_not_linked"),
        ), menu=True)

    async def cmd_paycontrol(self, chat_id: int, telegram_user_id: int, argument: str) -> None:
        if argument.strip():
            await self.apply_pay_instructions(chat_id, telegram_user_id, argument)
            return
        current = await service.get_pay_instructions()
        await self._say_admin(chat_id, "💳 Реквизиты для оплаты\n\n" + (current.strip() or "Реквизиты пока не заданы."), reply_markup={"inline_keyboard": [[ui.button("edit_requisites", "✏️ Изменить реквизиты")], [ui.button("menu")]]})

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
            if receipt_bytes or r.receipt_file_id:
                try:
                    sent = await self._send_receipt_to_admin(
                        chat_id, r.receipt_file_id or "", r.receipt_mime,
                        caption, keyboard, receipt_bytes,
                    )
                except (TelegramApiError, TelegramTransportError) as e:
                    logger.debug(f"Could not resend receipt for {r.public_code}: {e}")
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

        action = command.lstrip("/")
        permission = ui.PERMISSIONS.get("history" if action == "topups" else action)
        if permission and not await self._allowed(telegram_user_id, permission):
            return
        if command in ("/start", "/menu"):
            if command == "/start":
                await self._say_admin(chat_id, "👋 Добро пожаловать в панель администратора Dastyor!", menu=True)
            await self.cmd_menu(chat_id)
            return
        if command == "/help":
            await self._say_admin(chat_id, ui.HELP_TEXT)
            return
        if command in ("/addadmin", "/deladmin") and not argument:
            self._state(chat_id).admin_action = "add" if command == "/addadmin" else "remove"
            await self._say_admin(chat_id, "👤 Пришлите 6-значный ID аккаунта Dastyor или известный боту @username.")
            return

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
            await self._say_admin(chat_id, "\n".join(lines), reply_markup={"inline_keyboard": [[ui.button("addadmin")], [ui.button("deladmin")], [ui.button("menu")]]})
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

            if not delivered:
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

        await self.cmd_menu(chat_id)

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
            admin_name = await self._verify_token(self.admin_client, "admin")
            logger.info(f"Administrator bot online: @{admin_name}")
            try:
                await service.prune_processed_updates()
            except Exception as e:
                logger.warning(f"Processed-update prune skipped: {e}")
            await self._register_menu()
            await self._poll("admin", self.admin_client, self.handle_admin_update)
        finally:
            await self._close_clients()

    async def _register_menu(self) -> None:
        await self.admin_client.set_my_commands(ADMIN_MENU_COMMANDS)


    async def _close_clients(self) -> None:
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

    if not settings.TELEGRAM_ADMIN_BOT_TOKEN.strip():
        logger.error("TELEGRAM_ADMIN_BOT_TOKEN is not set in backend/.env or the environment")
        return 2
    if not await service.all_admin_ids():
        logger.error(
            "No Telegram reviewers are configured. Set TELEGRAM_ADMIN_IDS or "
            "grant at least one administrator in the database."
        )
        return 2
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
