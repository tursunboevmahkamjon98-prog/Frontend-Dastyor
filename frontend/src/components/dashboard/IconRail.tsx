"use client";

import Link from "next/link";
import { CreditCard, Plus, UserRound } from "lucide-react";
import { NAV_GROUPS, CREATE_HREF, isActive } from "@/lib/dashboard-nav";
import Logo from "@/components/Logo";
import ThemeToggle from "@/components/ThemeToggle";
import { useT } from "@/lib/i18n";

const mainItems = NAV_GROUPS[0].items;

export default function IconRail({
  pathname,
  avatarNode,
}: {
  pathname: string;
  avatarNode: React.ReactNode;
}) {
  const t = useT();
  const creating = pathname.startsWith(CREATE_HREF);
  const billing = isActive(pathname, "/dashboard/billing");
  const profile = isActive(pathname, "/dashboard/profile");

  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-56 flex-col border-r border-border-light bg-surface/95 px-3.5 py-6 shadow-[4px_0_24px_rgba(71,45,39,0.025)] backdrop-blur lg:flex">
      <Link href="/dashboard" aria-label="Dastyor" className="mb-9 flex h-10 items-center px-3">
        <Logo height="2rem" />
      </Link>

      <Link
        href={CREATE_HREF}
        aria-label={t("nav.create")}
        title={t("nav.create")}
        aria-current={creating ? "page" : undefined}
        className="mb-5 flex h-11 items-center gap-3 rounded-xl bg-primary px-3 text-sm font-semibold text-white shadow-card-lift transition-colors duration-150 hover:bg-primary-dark"
      >
        <Plus className="h-5 w-5" strokeWidth={2.2} />{t("nav.create")}
      </Link>

      <nav aria-label={t("nav.groupMain")} className="flex w-full flex-col gap-1">
        {mainItems.map(({ href, labelKey, icon: Icon, exact }) => {
          const active = isActive(pathname, href, exact);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              aria-label={t(labelKey)}
              title={t(labelKey)}
              className={active
                ? "flex h-10 items-center gap-3 rounded-xl bg-primary-50 px-3 text-sm font-semibold text-primary-accent"
                : "flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium text-text-secondary transition-colors duration-150 hover:bg-surface-muted hover:text-text-primary"}
            >
              <Icon className="h-4.5 w-4.5 shrink-0" strokeWidth={active ? 2.3 : 1.9} />{t(labelKey)}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex w-full flex-col gap-1 border-t border-border pt-3">
        <Link href="/dashboard/billing" aria-current={billing ? "page" : undefined}
          aria-label={t("nav.balance")} title={t("nav.balance")}
          className={billing
            ? "flex h-10 items-center gap-3 rounded-xl bg-primary-50 px-3 text-sm font-semibold text-primary-accent"
            : "flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium text-text-secondary hover:bg-surface-muted"}>
          <CreditCard className="h-4.5 w-4.5" strokeWidth={1.9} />{t("nav.balance")}
        </Link>
        <Link href="/dashboard/profile" aria-current={profile ? "page" : undefined}
          aria-label={t("nav.profile")} title={t("nav.profile")}
          className={profile ? "flex h-10 items-center gap-3 rounded-xl bg-primary-50 px-3 text-sm font-semibold text-primary-accent" : "flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium text-text-secondary hover:bg-surface-muted"}>
          <UserRound className="h-4.5 w-4.5" />{t("nav.profile")}
        </Link>
        <div className="flex items-center gap-3 px-3 pt-2">{avatarNode}<ThemeToggle className="h-9 w-9 rounded-xl" /></div>
      </div>
    </aside>
  );
}
