"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, Check, Clock3, CreditCard, FileImage, LoaderCircle, Wallet } from "lucide-react";
import { ApiError, billingApi, type BillingTopupRequest } from "@/lib/api";

type Bank = "Eskhata" | "Dushanbe City";
const banks: { id: Bank; short: string; style: string; logo?: string }[] = [
  { id: "Eskhata", short: "E", style: "from-sky-500 to-blue-700", logo: "/eskhata-bank-logo.svg" },
  { id: "Dushanbe City", short: "DC", style: "from-violet-500 to-indigo-700", logo: "/dushanbe-city-bank-logo.svg" },
];

const statusLabel: Record<string, string> = {
  pending: "Tekshiruvda", awaiting_receipt: "Chek kutilmoqda", needs_info: "Qo‘shimcha chek kerak",
  approved: "Tasdiqlandi", rejected: "Rad etildi", cancelled: "Bekor qilindi",
};

export default function BillingPage() {
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
    load().catch(() => setError("Ma’lumotlarni yuklab bo‘lmadi."));
    const timer = window.setInterval(() => { load().catch(() => undefined); }, 20000);
    return () => window.clearInterval(timer);
  }, [load]);

  const bankInstructions = useMemo(() => {
    const blocks = instructions.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
    const aliases = bank === "Eskhata" ? ["eskhata", "эсхата"] : ["dushanbe city", "душанбе сити"];
    return blocks.find((line) => aliases.some((alias) => line.toLowerCase().includes(alias))) ?? "";
  }, [instructions, bank]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSuccess("");
    const somoni = Number(amount);
    if (!Number.isInteger(somoni) || somoni < 5 || somoni > 100) return setError("Miqdor 5–100 somoni, butun son bo‘lishi kerak.");
    if (!bankInstructions) return setError("Bu bank uchun to‘lov rekvizitlari sozlanmagan.");
    if (!receipt) return setError("O‘tkazma chekini yuklang.");
    setBusy(true);
    try {
      await billingApi.submitTopup({ amount: somoni, bank, wallet: wallet.trim(), receipt });
      setSuccess("So‘rov adminga yuborildi. Balans admin tasdiqlagandan keyin yangilanadi.");
      setWallet(""); setReceipt(null); setAmount("5");
      const input = document.getElementById("receipt-file") as HTMLInputElement | null;
      if (input) input.value = "";
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "So‘rov yuborilmadi. Qayta urinib ko‘ring.");
    } finally { setBusy(false); }
  }

  return <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:py-10">
    <div className="mb-7 flex items-center gap-3">
      <Link href="/dashboard/profile" aria-label="Orqaga" className="grid h-10 w-10 place-items-center rounded-2xl border border-border-light bg-surface text-text-secondary shadow-sm"><ArrowLeft size={18}/></Link>
      <div><p className="text-sm font-semibold text-text-primary">Balans</p><p className="text-xs text-text-tertiary">Hisobni to‘ldirish va so‘rovlar</p></div>
    </div>

    <div className="grid gap-6 lg:grid-cols-[1.1fr_.9fr]">
      <section className="space-y-5">
        <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-6 text-white shadow-xl shadow-indigo-950/15">
          <div className="absolute -right-8 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl"/><div className="absolute bottom-0 right-20 h-20 w-20 rounded-full bg-indigo-400/20 blur-2xl"/>
          <div className="relative flex items-center gap-3"><div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/10 shadow-inner"><Wallet size={22}/></div><div><p className="text-sm text-white/65">Joriy balans</p><p className="text-3xl font-bold tracking-tight">{balance === null ? "—" : `${balance.toFixed(2)} сомони`}</p></div></div>
          <p className="relative mt-5 max-w-sm text-sm leading-6 text-white/65">To‘lovni yuboring va chekni biriktiring. Balans faqat admin bank tushumini tekshirib tasdiqlagach to‘ldiriladi.</p>
        </div>

        <form onSubmit={submit} className="rounded-[28px] border border-border-light bg-surface p-5 shadow-sm sm:p-7">
          <div className="mb-5 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-primary/10 text-primary"><CreditCard size={19}/></div><div><h1 className="font-semibold text-text-primary">Balansni to‘ldirish</h1><p className="text-xs text-text-tertiary">5 dan 100 somonigacha</p></div></div>

          <p className="mb-2 text-sm font-medium text-text-primary">Bankni tanlang</p>
          <div className="grid grid-cols-2 gap-3">
            {banks.map((item) => <button key={item.id} type="button" onClick={() => setBank(item.id)} aria-pressed={bank === item.id} className={`flex items-center gap-3 rounded-2xl border p-3 text-left transition ${bank === item.id ? "border-primary bg-primary/5 ring-2 ring-primary/10" : "border-border-light hover:bg-slate-50"}`}>
              <span className={`grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-gradient-to-br ${item.style} text-xs font-black tracking-wide text-white shadow-lg`}>{item.logo ? <Image src={item.logo} alt="Dushanbe City Bank" width={38} height={30} className="h-8 w-10 object-contain"/> : item.short}</span><span className="text-sm font-semibold text-text-primary">{item.id}</span>{bank === item.id && <Check className="ml-auto text-primary" size={17}/ >}
            </button>)}
          </div>

          <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-text-secondary">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-tertiary">O‘tkazma rekviziti</p>
            {bankInstructions || <span className="text-amber-700">Bu bank rekviziti admin tomonidan hali sozlanmagan.</span>}
          </div>

          <label className="mt-5 block text-sm font-medium text-text-primary">O‘tkazgan hamyon raqamingiz
            <input required minLength={5} maxLength={64} value={wallet} onChange={(e) => setWallet(e.target.value)} placeholder="+992 …" className="mt-2 w-full rounded-2xl border border-border-light bg-white px-4 py-3 text-sm outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10" />
          </label>
          <label className="mt-4 block text-sm font-medium text-text-primary">Miqdor (somoni)
            <div className="relative mt-2"><input required type="number" min={5} max={100} step={1} value={amount} onChange={(e) => setAmount(e.target.value)} className="w-full rounded-2xl border border-border-light bg-white px-4 py-3 pr-20 text-sm outline-none focus:border-primary focus:ring-4 focus:ring-primary/10"/><span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-text-tertiary">сомони</span></div>
          </label>
          <label className="mt-4 block text-sm font-medium text-text-primary">To‘lov cheki
            <span className="mt-2 flex cursor-pointer items-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-4 hover:border-primary">
              <FileImage size={20} className="text-primary"/><span className="min-w-0 flex-1 truncate text-sm text-text-secondary">{receipt?.name ?? "Rasm yoki PDF tanlang (8 MB gacha)"}</span>
              <input id="receipt-file" required type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="sr-only" onChange={(e) => setReceipt(e.target.files?.[0] ?? null)} />
            </span>
          </label>
          <p className="mt-3 text-xs leading-5 text-text-tertiary">Chek yuborilgani to‘lov tasdiqlandi degani emas. Admin bank hisobini tekshiradi.</p>
          {error && <p role="alert" className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p>}
          {success && <p role="status" className="mt-4 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</p>}
          <button disabled={busy} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/20 transition hover:brightness-105 disabled:opacity-60">{busy && <LoaderCircle size={17} className="animate-spin"/>}{busy ? "Yuborilmoqda…" : "Chekni yuborish"}</button>
        </form>
      </section>

      <aside className="rounded-[28px] border border-border-light bg-surface p-5 shadow-sm sm:p-7">
        <div className="mb-5 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-2xl bg-amber-50 text-amber-600"><Clock3 size={19}/></div><div><h2 className="font-semibold text-text-primary">To‘lovlar tarixi</h2><p className="text-xs text-text-tertiary">Oxirgi so‘rovlaringiz</p></div></div>
        {history.length === 0 ? <div className="rounded-2xl bg-slate-50 px-4 py-8 text-center text-sm text-text-tertiary">Hozircha so‘rov yo‘q.</div> : <ul className="space-y-3">{history.map((item) => <li key={item.id} className="rounded-2xl border border-border-light p-4">
          <div className="flex items-start justify-between gap-3"><div><p className="font-semibold text-text-primary">{item.requested_somoni.toFixed(2)} сомони</p><p className="mt-1 text-xs text-text-tertiary">{item.note || "Balansni to‘ldirish"}</p></div><span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.status === "approved" ? "bg-emerald-50 text-emerald-700" : item.status === "rejected" ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-700"}`}>{statusLabel[item.status] ?? item.status}</span></div>
          <p className="mt-3 text-[11px] text-text-tertiary">{new Date(item.created_at).toLocaleString("uz-UZ")}</p>
          {item.admin_note && <p className="mt-2 text-xs text-text-secondary">Admin izohi: {item.admin_note}</p>}
        </li>)}</ul>}
      </aside>
    </div>
  </main>;
}
