"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, Check, Clock3, CreditCard, FileImage, LoaderCircle, Wallet } from "lucide-react";
import { ApiError, billingApi, type BillingTopupRequest } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";

type Bank = "Eskhata" | "Dushanbe City";
const banks: { id: Bank; logo: string; logoWidth: number; logoHeight: number }[] = [
  { id: "Eskhata", logo: "/eskhata-bank-logo.png", logoWidth: 64, logoHeight: 36 },
  { id: "Dushanbe City", logo: "/dushanbe-city-bank-logo.png", logoWidth: 36, logoHeight: 36 },
];

const statusKey: Record<string, MessageKey> = {
  pending: "billing.statusPending",
  awaiting_receipt: "billing.statusAwaitingReceipt",
  needs_info: "billing.statusNeedsInfo",
  approved: "billing.statusApproved",
  rejected: "billing.statusRejected",
  cancelled: "billing.statusCancelled",
};

export default function BillingPage() {
  const t = useT();
  const { locale } = useLocale();
  const [balance, setBalance] = useState<number | null>(null);
  const [instructions, setInstructions] = useState("");
  const [history, setHistory] = useState<BillingTopupRequest[]>([]);
  const [bank, setBank] = useState<Bank>("Eskhata");
  const [amount, setAmount] = useState("5");
  const [wallet, setWallet] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    const [b, text, requests] = await Promise.all([
      billingApi.balance(), billingApi.payInstructions(), billingApi.topupHistory(),
    ]);
    setBalance(b.balance_somoni);
    setInstructions(text.text);
    setHistory(requests);
  }, []);

  useEffect(() => {
    load().catch(() => setError(t("billing.loadFailed")));
    const timer = window.setInterval(() => { load().catch(() => undefined); }, 20000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const bankInstructions = useMemo(() => {
    const blocks = instructions.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
    const aliases = bank === "Eskhata"
      ? ["eskhata", "эсхата"]
      : ["dushanbe city", "душанбе сити", "dc", "дс"];
    return blocks.find((line) => aliases.some((alias) => line.toLowerCase().includes(alias))) ?? "";
  }, [instructions, bank]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess("");
    const somoni = Number(amount);
    if (!Number.isInteger(somoni) || somoni < 5 || somoni > 100) return setError(t("billing.amountRange"));
    if (!bankInstructions) return setError(t("billing.bankRequired"));
    if (!receipt) return setError(t("billing.receiptRequired"));
    setBusy(true);
    try {
      await billingApi.submitTopup({ amount: somoni, bank, wallet: wallet.trim(), receipt });
      setSuccess(t("billing.submitted"));
      setWallet(""); setReceipt(null); setAmount("5");
      const input = document.getElementById("receipt-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("billing.submitFailed"));
    } finally { setBusy(false); }
  }

  return <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:py-10">
    <div className="mb-7 flex items-center gap-3">
      <Link href="/dashboard/profile" aria-label={t("common.back")} className="grid h-10 w-10 place-items-center rounded-2xl border border-border-light bg-white text-text-secondary shadow-[0_2px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5"><ArrowLeft size={18}/></Link>
      <div><p className="text-sm font-semibold text-text-primary">{t("billing.title")}</p><p className="text-xs text-text-tertiary">{t("billing.subtitle")}</p></div>
    </div>

    <div className="grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
      <section className="space-y-5">
        <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-primary-light via-primary to-primary-dark p-6 text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_20px_40px_-12px_rgba(220,38,38,0.4)]">
          <div className="pointer-events-none absolute -right-8 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl"/><div className="pointer-events-none absolute bottom-0 right-20 h-20 w-20 rounded-full bg-black/10 blur-2xl"/>
          <div className="relative flex items-center gap-3"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)]"><Wallet size={22}/></div><div><p className="text-sm text-white/70">{t("billing.current")}</p><p className="text-3xl font-bold tracking-tight">{balance === null ? "—" : `${balance.toFixed(2)} ${t("nav.somoni")}`}</p></div></div>
          <p className="relative mt-5 max-w-sm text-sm leading-6 text-white/75">{t("billing.heroDesc")}</p>
        </div>

        <form onSubmit={submit} className="rounded-[28px] border border-border-light bg-white p-5 shadow-[0_3px_0_0_var(--color-border-light),0_18px_36px_-14px_rgba(220,38,38,0.12)] sm:p-7">
          <div className="mb-5 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-primary-50 text-primary shadow-[inset_0_-2px_3px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.8)]"><CreditCard size={19}/></div><div><h1 className="font-semibold text-text-primary">{t("billing.formTitle")}</h1><p className="text-xs text-text-tertiary">{t("billing.formRange")}</p></div></div>

          <p className="mb-2 text-sm font-medium text-text-primary">{t("billing.chooseBank")}</p>
          <div className="grid grid-cols-2 gap-3">
            {banks.map((item) => <button key={item.id} type="button" onClick={() => setBank(item.id)} aria-pressed={bank === item.id} className={`flex items-center gap-3 rounded-2xl border p-3 text-left transition-all duration-150 ${bank === item.id ? "border-primary bg-primary-50 shadow-[0_3px_0_0_var(--color-primary-50)]" : "border-border-light bg-white shadow-[0_2px_0_0_var(--color-border-light)] hover:-translate-y-0.5"}`}>
              <span className="flex h-12 shrink-0 items-center justify-center rounded-2xl border border-border-light bg-white px-3 shadow-[0_2px_6px_rgba(0,0,0,0.08)]"><Image src={item.logo} alt={item.id} width={item.logoWidth} height={item.logoHeight} className="h-9 w-auto object-contain"/></span><span className="text-sm font-semibold text-text-primary">{item.id}</span>{bank === item.id && <Check className="ml-auto text-primary" size={17}/ >}
            </button>)}
          </div>

          <div className="mt-4 rounded-2xl border border-border-light bg-surface-muted p-4 text-sm text-text-secondary">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-tertiary">{t("billing.transferDetails")}</p>
            {bankInstructions || <span className="text-warning">{t("billing.bankNotConfigured")}</span>}
          </div>

          <label className="mt-5 block text-sm font-medium text-text-primary">{t("billing.walletLabel")}
            <input required minLength={5} maxLength={64} value={wallet} onChange={(e) => setWallet(e.target.value)} placeholder="+992 …" className="mt-2 w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-text-primary shadow-[inset_0_2px_3px_rgba(0,0,0,0.04)] outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
          </label>
          <label className="mt-4 block text-sm font-medium text-text-primary">{t("billing.amountLabel")}
            <div className="relative mt-2"><input required type="number" min={5} max={100} step={1} value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full rounded-2xl border border-border bg-white px-4 py-3 pr-20 text-sm text-text-primary shadow-[inset_0_2px_3px_rgba(0,0,0,0.04)] outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10"/><span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">{t("nav.somoni")}</span></div>
          </label>
          <label className="mt-4 block text-sm font-medium text-text-primary">{t("billing.receiptLabel")}
            <span className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-dashed border-border bg-surface-muted px-4 py-4 transition-colors hover:border-primary">
              <FileImage size={20} className="text-primary"/><span className="min-w-0 flex-1 truncate text-sm text-text-secondary">{receipt?.name ?? t("billing.receiptPlaceholder")}</span>
              <input id="receipt-file" required type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="sr-only" onChange={(e) => setReceipt(e.target.files?.[0] ?? null)} />
            </span>
          </label>
          <p className="mt-3 text-xs leading-5 text-text-tertiary">{t("billing.receiptNote")}</p>
          {error && <p role="alert" className="mt-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</p>}
          {success && <p role="status" className="mt-4 rounded-xl border border-success/20 bg-success/10 px-4 py-3 text-sm text-success">{success}</p>}
          <button disabled={busy} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-b from-primary-light to-primary px-5 py-3.5 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_12px_24px_-6px_rgba(220,38,38,0.4)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_16px_28px_-6px_rgba(220,38,38,0.45)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-60">{busy && <LoaderCircle size={17} className="animate-spin"/>}{busy ? t("billing.sending") : t("billing.submitReceipt")}</button>
        </form>
      </section>

      <aside className="rounded-[28px] border border-border-light bg-white p-5 shadow-[0_3px_0_0_var(--color-border-light),0_18px_36px_-14px_rgba(0,0,0,0.08)] sm:p-7">
        <div className="mb-5 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-lecture-bg text-lecture-icon shadow-[inset_0_-2px_3px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.8)]"><Clock3 size={19}/></div><div><h2 className="font-semibold text-text-primary">{t("billing.history")}</h2><p className="text-xs text-text-tertiary">{t("billing.historySubtitle")}</p></div></div>
        {history.length === 0 ? <div className="rounded-2xl border border-dashed border-border-light bg-surface-muted px-4 py-8 text-center text-sm text-text-tertiary">{t("billing.noRequests")}</div> : <ul className="space-y-3">{history.slice(0, 5).map((item) => <li key={item.id} className="rounded-2xl border border-border-light bg-white p-4 shadow-[0_2px_0_0_var(--color-border-light)]">
          <div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-text-primary">{item.requested_somoni.toFixed(2)} {t("nav.somoni")}</p><p className="mt-1 text-xs text-text-tertiary">{item.note || t("billing.formTitle")}</p></div><span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.status === "approved" ? "bg-success/10 text-success" : item.status === "rejected" ? "bg-primary-50 text-primary-dark" : "bg-lecture-bg text-lecture-icon"}`}>{statusKey[item.status] ? t(statusKey[item.status]) : item.status}</span></div>
          <p className="mt-3 text-[11px] text-text-tertiary">{new Date(item.created_at).toLocaleString(locale)}</p>
          {item.admin_note && <p className="mt-2 text-xs text-text-secondary">{t("billing.adminNote")}{item.admin_note}</p>}
        </li>)}</ul>}
      </aside>
    </div>
  </main>;
}
