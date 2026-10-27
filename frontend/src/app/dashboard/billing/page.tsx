"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Loader2, Wallet, XCircle } from "lucide-react";
import { billingApi, ApiError, type TopupRequestOut } from "@/lib/api";
import { ErrorNote } from "@/components/ui";
import { useT } from "@/lib/i18n";

/** Telegram's paper plane.
 *
 * Inline rather than from lucide, which has no Telegram brand mark (its
 * `Send` is a generic arrow). Same geometry as the Flutter app's
 * TelegramGlyph, so the two clients show the same button.
 *
 * `aria-hidden`: the button around it carries the label, and announcing
 * the logo too would read the name twice.
 */
function TelegramGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M22.6 2.9 1.4 11.4l7.2 2.9v7l3.5-5 6.3 4.8z" fillOpacity="1" />
      <path d="M8.6 14.3 22.6 2.9l-10.5 13.4z" fillOpacity="0.55" />
    </svg>
  );
}

/**
 * Balance, and how to add to it.
 *
 * This page used to be read-only вЂ” a number and a paragraph telling the
 * teacher to phone the administrator. The Telegram block below is the
 * first top-up route the page can actually start.
 *
 * What it still does not do: take payment. No card form, no checkout, no
 * gateway. It hands off to a bot; a human transfers money through their
 * own bank; an administrator confirms it. No money moves through this
 * code, and the balance changes server-side only after that
 * confirmation вЂ” which is why the copy says so instead of implying the
 * receipt itself is enough.
 *
 * A modified client cannot grant credit either: `/billing/telegram/link`
 * only mints an account-linking token.
 *
 * The balance and the three-step Telegram action are separate cards on
 * desktop and stack on mobile. Link issuance is always attempted by the
 * backend on click; status is shown as guidance, never used to make the
 * main action silently unresponsive.
 */
export default function BillingPage() {
  const t = useT();
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [telegram, setTelegram] = useState<{
    linked: boolean;
    configured: boolean;
    botUsername: string;
  }>({ linked: false, configured: false, botUsername: "" });
  const [opening, setOpening] = useState(false);
  const [telegramError, setTelegramError] = useState<string | null>(null);
  // The manual six-digit code route вЂ” shown as soon as a link is
  // minted, not as a guess about whether the automatic tab worked. It
  // is the one path that needs no link to resolve at all, which is
  // what makes it the real fallback for an ISP that blocks t.me.
  const [manual, setManual] = useState<
    { botUsername: string; code: string } | null
  >(null);
  const [copied, setCopied] = useState(false);
  // "idle": nothing in flight. "pending": a token was minted and we're
  // polling the backend to see whether the bot has redeemed it.
  // "confirmed"/"expired" are terminal вЂ” set once, cleared on the next click.
  const [linkFlow, setLinkFlow] = useState<"idle" | "pending" | "confirmed" | "expired">(
    "idle"
  );
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
    };
  }, []);

  const [myRequests, setMyRequests] = useState<TopupRequestOut[]>([]);

  const reloadMyRequests = useCallback(() => {
    billingApi.myTopupRequests().then(setMyRequests).catch(() => {});
  }, []);

  useEffect(() => {
    billingApi
      .balance()
      .then((b) => setBalance(b.balance_somoni))
      // Empty string means "no specific server message", resolved to the
      // generic text at render time rather than here. That keeps `t` out
      // of this effect's dependencies, and means an error raised before
      // the reader switches language is re-rendered in the new one.
      .catch((err) => setError(err instanceof ApiError ? err.message : ""))
      .finally(() => setLoading(false));

    // Separate from the balance call, and its failure is swallowed: this
    // only decides whether an optional block is drawn, and failing the
    // page because a secondary request timed out would hide the number
    // the teacher came for.
    billingApi
      .telegramStatus()
      .then((s) => setTelegram({
        linked: s.linked,
        configured: s.bot_configured,
        botUsername: s.bot_username,
      }))
      .catch(() => setTelegram({ linked: false, configured: false, botUsername: "" }));

    reloadMyRequests();
  }, [reloadMyRequests]);

  const openTelegram = useCallback(async () => {
    if (opening) return;
    setOpening(true);
    setTelegramError(null);
    setLinkFlow("idle");
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }

    try {
      // A linked account only needs to reopen the bot. Do not mint another
      // one-time token for an already completed link.
      if (telegram.linked && telegram.botUsername) {
        window.location.href = `tg://resolve?domain=${telegram.botUsername}`;
        return;
      }

      const link = await billingApi.telegramCode();

      setManual({ botUsername: link.bot_username, code: link.code });
      setCopied(false);
      setLinkFlow("pending");

      // Open Telegram through its local protocol handler. The copyable
      // six-digit code below is the fallback when no Telegram app
      // is registered for tg:// on this device.
      window.location.href = `tg://resolve?domain=${link.bot_username}`;

      // Opening a tab is not linking. The account is linked only once the
      // bot has actually received and redeemed /start <token>, which this
      // page cannot observe directly вЂ” so it asks the backend, which is
      // the only party that knows. Polling stops on success, on the
      // token's own expiry, or when a fresh click restarts the flow.
      const expiresAtMs = new Date(link.expires_at).getTime();
      pollRef.current = window.setInterval(async () => {
        if (Date.now() > expiresAtMs) {
          if (pollRef.current !== null) window.clearInterval(pollRef.current);
          pollRef.current = null;
          setLinkFlow("expired");
          return;
        }
        try {
          const status = await billingApi.telegramStatus();
          if (status.linked) {
            if (pollRef.current !== null) window.clearInterval(pollRef.current);
            pollRef.current = null;
            setTelegram({
              linked: true,
              configured: status.bot_configured,
              botUsername: status.bot_username,
            });
            setManual(null);
            setLinkFlow("confirmed");
          }
        } catch {
          // Transient network hiccup вЂ” the next tick tries again; the
          // token's own expiry is still the hard stop.
        }
      }, 3000);
    } catch (err) {
      setLinkFlow("idle");
      setTelegramError(
        err instanceof ApiError ? err.message : t("billing.telegramFailed")
      );
    } finally {
      setOpening(false);
    }
  }, [opening, telegram.botUsername, telegram.linked, t]);

  const telegramSteps = [
    t("billing.telegramStep1"),
    t("billing.telegramStep2"),
    t("billing.telegramStep3"),
  ];

  return (
    <div className="mx-auto w-full max-w-[960px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <div className="mb-7 flex items-center gap-3.5">
        <Link
          href="/dashboard/profile"
          aria-label={t("common.back")}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border-light bg-surface transition-colors duration-150 hover:bg-surface-muted"
        >
          <ArrowLeft className="h-4 w-4 text-text-primary" strokeWidth={2} />
        </Link>
        <div>
          <h1 className="text-heading font-semibold text-text-primary">{t("billing.title")}</h1>
          <p className="mt-0.5 text-meta text-text-tertiary">{t("billing.subtitle")}</p>
        </div>
      </div>

      {error !== null && <ErrorNote>{error || t("common.error")}</ErrorNote>}

      <div className="mb-5 grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.35fr)]">
        <section className="relative overflow-hidden rounded-card bg-gradient-to-br from-primary to-primary-dark p-6 text-white shadow-sm sm:p-7">
          <div className="absolute -right-8 -top-10 h-40 w-40 rounded-full border-[24px] border-white/10" aria-hidden="true" />
          <div className="relative flex items-center justify-between gap-3">
            <p className="text-micro font-semibold uppercase tracking-[0.14em] text-white/75">
              {t("billing.current")}
            </p>
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15">
              <Wallet className="h-5 w-5" strokeWidth={2} />
            </span>
          </div>
          <p className="relative mt-5 text-3xl font-bold tabular-nums tracking-tight sm:text-4xl">
            {loading ? "вЂ¦" : `${(balance ?? 0).toFixed(2)} ${t("nav.somoni")}`}
          </p>
          <p className="relative mt-2 max-w-xs text-micro leading-relaxed text-white/75">
            {t("billing.balanceNote")}
          </p>
        </section>

        <section className="rounded-card border border-border-light bg-surface p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-50">
              <TelegramGlyph className="h-5 w-5 text-primary-accent" />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-body font-semibold text-text-primary">
                {t("billing.telegramTitle")}
              </h2>
              {telegram.linked && (
                <p className="mt-1 text-micro text-success">
                  {t("billing.telegramLinkedNote")}
                </p>
              )}
            </div>
            {telegram.linked && (
              <CheckCircle2 className="mt-1 h-5 w-5 shrink-0 text-success" aria-hidden="true" />
            )}
          </div>

          <p className="mt-4 text-meta leading-relaxed text-text-secondary">
            {t("billing.telegramBody")}
          </p>

          <ol className="mt-5 grid gap-2 sm:grid-cols-3">
            {telegramSteps.map((step, index) => (
                <li key={step} className="flex items-start gap-2 rounded-control bg-surface-muted p-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-50 text-micro font-bold text-primary-accent">
                    {index + 1}
                  </span>
                  <span className="pt-0.5 text-micro leading-snug text-text-secondary">
                    {step}
                  </span>
                </li>
              ))}
          </ol>

          <button
            type="button"
            onClick={openTelegram}
            disabled={opening}
            aria-describedby={!telegram.configured ? "telegram-config-note" : undefined}
            className="mt-5 flex min-h-[3.5rem] w-full items-center justify-center gap-2.5 rounded-xl bg-primary px-4 py-3 text-meta font-semibold text-white shadow-sm transition-colors duration-150 hover:bg-primary-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-wait disabled:opacity-60"
          >
            {opening ? (
              <Loader2 className="h-4.5 w-4.5 shrink-0 animate-spin" aria-hidden="true" />
            ) : (
              <TelegramGlyph className="h-4.5 w-4.5 shrink-0" />
            )}
            <span className="text-center leading-snug">
              {telegram.linked
                ? t("billing.telegramButtonLinked")
                : t("billing.telegramButton")}
            </span>
          </button>

          {!telegram.configured && (
            <p id="telegram-config-note" className="mt-2.5 text-micro leading-relaxed text-text-tertiary">
              {t("billing.telegramUnavailable")}
            </p>
          )}

          {linkFlow === "pending" && (
            <p className="mt-3 flex items-center gap-2 text-micro leading-relaxed text-text-secondary">
              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" aria-hidden="true" />
              {t("billing.telegramPendingNote")}
            </p>
          )}

          {linkFlow === "confirmed" && (
            <p className="mt-3 flex items-center gap-2 text-micro font-semibold text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {t("billing.telegramLinkSuccess")}
            </p>
          )}

          {linkFlow === "expired" && (
            <p className="mt-3 flex items-center gap-2 text-micro text-primary-accent">
              <XCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {t("billing.telegramLinkExpired")}
            </p>
          )}

          {manual && (
            <div className="mt-3 rounded-control border border-border-light bg-surface-muted p-3.5">
              <p className="text-micro font-semibold text-text-primary">
                {t("billing.telegramManualTitle")}
              </p>
              <p className="mt-1 text-micro text-text-secondary">
                {t("billing.telegramCodeSafety")}
              </p>
              <p className="mt-1 text-micro leading-relaxed text-text-secondary">
                {t("billing.telegramManualStep1")}{" "}
                <span className="font-semibold text-text-primary">
                  @{manual.botUsername}
                </span>
                {". "}
                {t("billing.telegramManualStep2")}
              </p>
              <div className="mt-2.5 flex items-center gap-2">
                <code aria-label={t("billing.telegramCodeSafety")} className="min-w-0 flex-1 overflow-x-auto rounded-control bg-surface px-2.5 py-2 text-center font-mono text-xl font-bold tracking-[0.2em] text-text-primary">
                  {manual.code}
                </code>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(manual.code);
                      setCopied(true);
                    } catch {
                      // Clipboard is blocked on insecure origins and in
                      // some browsers; the command is selectable above,
                      // so this is not worth an error message.
                    }
                  }}
                  className="shrink-0 rounded-control border border-border-light px-2.5 py-2 text-micro font-semibold text-text-primary transition-colors duration-150 hover:bg-surface"
                >
                  {copied ? t("billing.telegramCopied") : t("billing.telegramCopy")}
                </button>
              </div>
            </div>
          )}

          {telegramError && (
            <p className="mt-2.5 text-micro text-primary-accent">{telegramError}</p>
          )}
        </section>
      </div>

      {myRequests.length > 0 && (
        <div className="mt-5 rounded-card border border-border-light bg-surface p-5 sm:p-6">
          <h2 className="mb-3 text-body font-semibold text-text-primary">{t("billing.myRequestsTitle")}</h2>
          <ul className="divide-y divide-border-light">
            {myRequests.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="text-meta font-semibold tabular-nums text-text-primary">
                    {r.requested_somoni.toFixed(2)} {t("nav.somoni")}
                  </p>
                  {r.note && <p className="truncate text-micro text-text-tertiary">{r.note}</p>}
                  {r.status === "approved" && r.credited_somoni !== null && (
                    <p className="text-micro text-success">
                      {t("billing.requestCreditedPrefix")} {r.credited_somoni.toFixed(2)} {t("nav.somoni")}
                    </p>
                  )}
                  {r.status === "rejected" && r.admin_note && (
                    <p className="text-micro text-error">{r.admin_note}</p>
                  )}
                </div>
                <span
                  className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-micro font-semibold ${
                    r.status === "approved"
                      ? "bg-success/10 text-success"
                      : r.status === "rejected"
                      ? "bg-error/10 text-error"
                      : "bg-warning/10 text-warning"
                  }`}
                >
                  {r.status === "approved" && <CheckCircle2 className="h-3.5 w-3.5" />}
                  {r.status === "rejected" && <XCircle className="h-3.5 w-3.5" />}
                  {r.status === "approved"
                    ? t("billing.completed")
                    : r.status === "rejected"
                    ? t("billing.requestRejected")
                    : t("billing.pending")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
