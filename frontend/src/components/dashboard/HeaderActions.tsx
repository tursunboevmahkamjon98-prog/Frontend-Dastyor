"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, Wallet } from "lucide-react";
import { billingApi, materialsApi, type SearchResultItem } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function HeaderActions({ name, balance, avatarNode, pathname }: {
  name: string;
  balance: number;
  avatarNode: React.ReactNode;
  pathname: string;
}) {
  const t = useT();
  const [liveBalance, setLiveBalance] = useState(balance);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<SearchResultItem[] | null>(null);

  useEffect(() => {
    let active = true;
    billingApi.balance().then((result) => { if (active) setLiveBalance(result.balance_somoni); }).catch(() => {});
    return () => { active = false; };
  }, [pathname, balance]);

  function toggleActivity() {
    if (!open) {
      materialsApi.search("").then((result) => setItems(result.slice(0, 4))).catch(() => setItems([]));
    }
    setOpen((value) => !value);
  }

  return <div className="relative flex shrink-0 items-center gap-2 sm:gap-3">
    <button type="button" onClick={toggleActivity} aria-label={t("nav.notifications")} aria-expanded={open}
      className="flex h-10 w-10 items-center justify-center rounded-xl border border-border text-text-secondary hover:bg-surface-muted">
      <Bell className="h-4.5 w-4.5" />
    </button>
    {open && <div className="absolute right-0 top-12 z-50 w-72 rounded-2xl border border-border bg-surface p-3 shadow-card-lift sm:w-80">
      <p className="mb-2 px-2 text-sm font-semibold text-text-primary">{t("nav.activity")}</p>
      {items === null ? <p className="px-2 py-3 text-sm text-text-tertiary">{t("common.loading")}</p>
        : items.length === 0 ? <p className="px-2 py-3 text-sm text-text-tertiary">{t("nav.activityEmpty")}</p>
          : items.map((item) => <Link key={`${item.type}:${item.id}`} href={`/dashboard/materials/${item.type}/${item.id}`} onClick={() => setOpen(false)}
            className="block truncate rounded-lg px-2 py-2 text-sm text-text-secondary hover:bg-surface-muted hover:text-text-primary">{item.title}</Link>)}
    </div>}
    <Link href="/dashboard/billing" className="flex h-10 items-center gap-2 rounded-xl border border-border px-2.5 text-xs font-semibold text-text-primary hover:bg-surface-muted sm:px-3 sm:text-sm" aria-label={`${t("nav.balance")}: ${liveBalance.toFixed(2)} ${t("nav.somoni")}`}>
      <Wallet className="h-4 w-4 text-primary-accent" />
      <span className="tabular-nums">{liveBalance.toFixed(2)} <span className="hidden sm:inline">{t("nav.somoni")}</span></span>
    </Link>
    <Link href="/dashboard/profile" className="hidden items-center gap-3 rounded-xl pl-1 sm:flex" aria-label={t("nav.profile")}>
      <span className="hidden max-w-36 truncate text-sm font-semibold text-text-primary xl:block">{name}</span>
      {avatarNode}
    </Link>
  </div>;
}
