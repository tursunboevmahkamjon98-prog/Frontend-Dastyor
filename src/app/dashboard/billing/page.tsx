"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Wallet } from "lucide-react";
import { billingApi, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";


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

        <p className="mt-4 text-xs leading-relaxed text-text-tertiary">{t("billing.priceNote")}</p>
      </div>
    </div>
  );
}
