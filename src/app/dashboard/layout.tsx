"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Home, Layers, PlusCircle, User, WifiOff, BookOpen, Wallet, LogOut, Gamepad2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useOnlineStatus } from "@/lib/use-online-status";
import { markBackNavigationListener } from "@/lib/back-navigation";
import { API_ORIGIN } from "@/lib/api";
import { useT, useAccountLocale } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";
import AppUpdateBanner from "@/components/AppUpdateBanner";
import BillingLink from "@/components/BillingLink";

type NavItem = { href: string; labelKey: MessageKey; icon: typeof Home; exact?: boolean; external?: boolean };


const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", labelKey: "nav.home", icon: Home, exact: true },
  { href: "/dashboard/materials", labelKey: "nav.materials", icon: Layers },
  { href: "/dashboard/lessons", labelKey: "nav.lessons", icon: BookOpen },
  { href: "/dashboard/create", labelKey: "nav.create", icon: PlusCircle },
  { href: "/dashboard/profile", labelKey: "nav.profile", icon: User },
];


const CREATE_ITEM = NAV_ITEMS.find((i) => i.href === "/dashboard/create")!;
const GAME_ITEM: NavItem = {
  href: "https://zehn.rahnamo.tj/",
  labelKey: "landing.feature.igra.title",
  icon: Gamepad2,
  external: true,
};
const SIDEBAR_ITEMS = NAV_ITEMS.filter((i) => i !== CREATE_ITEM).flatMap((item) =>
  item.href === "/dashboard/profile" ? [GAME_ITEM, item] : [item]
);



function isActive(pathname: string, href: string, exact?: boolean) {
  return exact ? pathname === href : pathname.startsWith(href);
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  const { user, loading, logout } = useAuth();
  useAccountLocale(user?.language);
  const router = useRouter();
  const pathname = usePathname();
  const online = useOnlineStatus();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  
  
  
  
  
  
  useEffect(() => markBackNavigationListener(), []);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-text-secondary">{t("common.loading")}</p>
      </div>
    );
  }

  const avatar = user.avatar_url ? `${API_ORIGIN}${user.avatar_url}` : null;

  return (
    <div className="min-h-screen bg-background">
      {!online && (
        <div className="sticky top-0 z-30 flex items-center justify-center gap-2 bg-primary px-4 py-2.5 text-center text-sm font-medium text-white">
          <WifiOff className="h-4 w-4 shrink-0" />
          {t("common.offline")}
        </div>
      )}

      <AppUpdateBanner />

      {}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-border-light bg-white lg:flex">
        <Link href="/dashboard" className="flex items-center gap-2.5 px-5 py-6">
          {}
          <img src="/brand/dastyor-mark.webp" alt="" className="h-8 w-auto" />
          <span className="text-lg font-bold text-text-primary">Dastyor</span>
        </Link>

        {}
        <Link
          href={CREATE_ITEM.href}
          className="mx-3 mb-4 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary px-3 py-2.5 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_4px_0_0_var(--color-primary-dark)] active:translate-y-px active:shadow-[0_1px_0_0_var(--color-primary-dark)]"
        >
          <CREATE_ITEM.icon className="h-4.5 w-4.5 shrink-0" strokeWidth={2.5} />
          {t(CREATE_ITEM.labelKey)}
        </Link>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {SIDEBAR_ITEMS.map(({ href, labelKey, icon: Icon, exact, external }) => {
            const active = !external && isActive(pathname, href, exact);
            const className = `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
              active
                ? "bg-primary-50 font-semibold text-primary"
                : "font-medium text-text-secondary hover:bg-surface-muted hover:text-text-primary"
            }`;
            const content = <><Icon className="h-5 w-5 shrink-0" strokeWidth={active ? 2.5 : 2} />{t(labelKey)}</>;
            return external ? (
              <a key={href} href={href} className={className}>{content}</a>
            ) : (
              <Link key={href} href={href} className={className}>{content}</Link>
            );
          })}
        </nav>

        {}
        <BillingLink
          className="group mx-3 mb-3 flex items-center gap-3 rounded-xl border border-border-light bg-white p-3 shadow-[0_2px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_3px_0_0_var(--color-border-light),0_8px_16px_-8px_rgba(220,38,38,0.15)]"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary shadow-[inset_0_-2px_3px_rgba(0,0,0,0.06),inset_0_1px_1px_rgba(255,255,255,0.8)] transition group-hover:scale-110">
            <Wallet className="h-4 w-4" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[11px] text-text-tertiary">{t("nav.balance")}</span>
            <span className="block truncate text-sm font-bold text-text-primary">
              {user.balance_somoni.toFixed(2)} {t("nav.somoni")}
            </span>
          </span>
          <span className="shrink-0 rounded-lg bg-gradient-to-b from-primary-light to-primary px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-[0_2px_0_0_var(--color-primary-dark)]">
            {t("profile.topUp")}
          </span>
        </BillingLink>

        {}
        <Link
          href="/dashboard/profile"
          className="m-3 flex items-center gap-3 rounded-xl px-3 py-3 transition hover:bg-surface-muted"
        >
          {avatar ? (
            
            <img src={avatar} alt="" className="h-9 w-9 shrink-0 rounded-full object-cover" />
          ) : (
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-50 text-sm font-semibold text-primary">
              {user.full_name.trim().charAt(0).toUpperCase()}
            </span>
          )}
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-text-primary">{user.full_name}</span>
            <span className="block truncate text-xs text-text-tertiary">{user.phone ?? user.email}</span>
          </span>
        </Link>

        <button
          type="button"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
          className="mx-3 mb-3 flex items-center gap-3 rounded-xl border border-border-light bg-white px-3 py-2.5 text-sm font-semibold text-text-secondary transition hover:border-primary/20 hover:bg-primary-50 hover:text-primary"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          {t("profile.logout")}
        </button>
      </aside>

      {}
      <main className="pb-20 lg:pb-10 lg:pl-64">{children}</main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-border-light bg-white/95 backdrop-blur lg:hidden">
        <div className="mx-auto flex max-w-md items-center justify-around px-2 py-2 sm:max-w-lg">
          {NAV_ITEMS.map(({ href, labelKey, icon: Icon, exact }) => {
            const active = isActive(pathname, href, exact);
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-col items-center gap-1 rounded-xl px-4 py-1.5 text-xs font-medium transition ${
                  active ? "text-primary" : "text-text-tertiary"
                }`}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.5 : 2} />
                {t(labelKey)}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
