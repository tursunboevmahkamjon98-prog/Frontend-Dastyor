"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Wallet, MessageCircle, Phone } from "lucide-react";
import { billingApi, ApiError } from "@/lib/api";
import { CONTACT } from "@/lib/contact";
import { useT } from "@/lib/i18n";

/** Balance, and the one way to add to it: talk to an administrator.
 *
 * There was a card-payment flow here (Dushanbe City: amount picker,
 * redirect to the bank, status polling). It is gone from the UI by an
 * explicit decision — a teacher tops up by contacting an administrator,
 * paying outside the app, and the administrator credits the balance from
 * the admin panel (backend/app/routers/admin.py's add_balance). What is
 * left is the number to reach and the current balance.
 */
export default function BillingPage() {
  const t = useT();
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    billingApi
      .balance()
      .then((b) => setBalance(b.balance_somoni))
      .catch((err) => setError(err instanceof ApiError ? err.message : t("common.error")))
      .finally(() => setLoading(false));
    // t is stable for a given locale and re-running this on a language
    // change would refetch the balance for nothing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-lg px-4 pt-6 sm:px-6">
      <div className="mb-5 flex items-center gap-3">
        <Link
          href="/dashboard/profile"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border-light bg-surface"
        >
          <ArrowLeft className="h-4 w-4 text-text-primary" />
        </Link>
        <div>
          <p className="font-bold text-text-primary">{t("billing.title")}</p>
          <p className="text-xs text-text-tertiary">{t("billing.subtitleAdmin")}</p>
        </div>
      </div>

      <div className="mb-6 flex items-center gap-4 rounded-2xl bg-primary p-5 text-white shadow-md shadow-primary/20">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/15">
          <Wallet className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-white/80">{t("billing.current")}</p>
          <p className="text-2xl font-bold">
            {loading ? "…" : `${(balance ?? 0).toFixed(2)} ${t("nav.somoni")}`}
          </p>
        </div>
      </div>

      {error && (
        <p className="mb-4 rounded-xl bg-primary-50 px-4 py-2.5 text-sm text-primary-dark">{error}</p>
      )}

      <div className="rounded-2xl border border-border-light bg-surface p-5">
        <h2 className="text-sm font-semibold text-text-primary">{t("billing.howToTitle")}</h2>
        <p className="mt-1.5 text-sm leading-relaxed text-text-secondary">
          {t("billing.howToBody")}
        </p>

        <div className="mt-4 space-y-2">
          <a
            href={`https://wa.me/${CONTACT.whatsappDigits}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl bg-primary px-4 py-3 text-white transition hover:bg-primary-dark"
          >
            <MessageCircle className="h-5 w-5 shrink-0" />
            <span className="flex-1 text-sm font-semibold">{t("billing.writeWhatsapp")}</span>
            <span className="text-sm text-white/85">{CONTACT.whatsapp}</span>
          </a>

          <a
            href={`tel:${CONTACT.phoneDigits}`}
            className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-text-primary transition hover:border-primary hover:bg-primary-50"
          >
            <Phone className="h-5 w-5 shrink-0 text-primary" />
            <span className="flex-1 text-sm font-semibold">{t("billing.callAdmin")}</span>
            <span className="text-sm text-text-secondary">{CONTACT.phone}</span>
          </a>
        </div>

        <p className="mt-4 text-xs leading-relaxed text-text-tertiary">{t("billing.priceNote")}</p>
      </div>
    </div>
  );
}
