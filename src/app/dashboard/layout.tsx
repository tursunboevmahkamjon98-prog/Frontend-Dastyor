"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Home, Layers, PlusCircle, User, WifiOff } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useOnlineStatus } from "@/lib/use-online-status";
import { markBackNavigationListener } from "@/lib/back-navigation";
import { API_ORIGIN } from "@/lib/api";
import { useT, useAccountLocale } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";

type NavItem = { href: string; labelKey: MessageKey; icon: typeof Home; exact?: boolean };

/** Every destination, in tab-bar order — the mobile bar renders all four. */
const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", labelKey: "nav.home", icon: Home, exact: true },
  { href: "/dashboard/materials", labelKey: "nav.materials", icon: Layers },
  { href: "/dashboard/create", labelKey: "nav.create", icon: PlusCircle },
  { href: "/dashboard/profile", labelKey: "nav.profile", icon: User },
];

/** The desktop sidebar promotes "create" to a filled button, so its list
 * holds everything else — derived from NAV_ITEMS rather than written out
 * again, so a future destination only has to be added in one place. */
const CREATE_ITEM = NAV_ITEMS.find((i) => i.href === "/dashboard/create")!;
const SIDEBAR_ITEMS = NAV_ITEMS.filter((i) => i !== CREATE_ITEM);

// Desktop-sidebar-only extra shortcut (not one of the four thumb-reached

function isActive(pathname: string, href: string, exact?: boolean) {
  return exact ? pathname === href : pathname.startsWith(href);
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  const { user, loading } = useAuth();
  useAccountLocale(user?.language);
  const router = useRouter();
  const pathname = usePathname();
  const online = useOnlineStatus();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  // Registered here, not on the page that needs it (the create screen):
  // this layout is the thing that stays mounted across every client-side
  // route change under /dashboard, which is exactly the span a Back-button
  // press has to be caught within. See back-navigation.ts for why the
  // previous approach (Performance Navigation Timing) never actually
  // fired.
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

      {/* Desktop only. Below lg the bottom tab bar below is the navigation —
          a phone browser wants thumb-reachable tabs, a laptop wants a
          persistent sidebar. Previously the tab bar was used at every
          breakpoint, which left a desktop window showing a narrow phone
          column stranded in the middle of a wide empty page. */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-border-light bg-surface lg:flex">
        <Link href="/dashboard" className="flex items-center gap-2.5 px-5 py-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="" className="h-8 w-8" />
          <span className="text-lg font-bold text-text-primary">Dastyor</span>
        </Link>

        {/* Creating a material is the one thing teachers come here to do, so
            on desktop it is a filled button rather than a fourth equal row
            in the list. The mobile tab bar below deliberately keeps it as a
            plain tab — a thumb-reached tab bar wants four equal targets, a
            sidebar wants a clear primary action. */}
        <Link
          href={CREATE_ITEM.href}
          className="mx-3 mb-4 flex items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:bg-primary-dark"
        >
          <CREATE_ITEM.icon className="h-4.5 w-4.5 shrink-0" strokeWidth={2.5} />
          {t(CREATE_ITEM.labelKey)}
        </Link>

        <nav className="flex flex-1 flex-col gap-1 px-3">
          {SIDEBAR_ITEMS.map(({ href, labelKey, icon: Icon, exact }) => {
            const active = isActive(pathname, href, exact);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-primary-50 font-semibold text-primary"
                    : "font-medium text-text-secondary hover:bg-surface-muted hover:text-text-primary"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" strokeWidth={active ? 2.5 : 2} />
                {t(labelKey)}
              </Link>
            );
          })}
        </nav>

        {/* The always-visible balance row was removed on purpose: paid
            top-ups are not live yet (see dashboard/billing), so a running
            somoni figure in the sidebar advertises a transaction a
            teacher cannot actually make. It still appears inside
            Profile → Billing, where the "not yet" is explained next to
            it. Put this back when payment goes live. */}
        <Link
          href="/dashboard/profile"
          className="m-3 flex items-center gap-3 rounded-xl px-3 py-3 transition hover:bg-surface-muted"
        >
          {avatar ? (
            // eslint-disable-next-line @next/next/no-img-element
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
      </aside>

      {/* pb-20 clears the fixed tab bar on phones; lg has no tab bar, and
          pl-64 makes room for the sidebar instead. */}
      <main className="pb-20 lg:pb-10 lg:pl-64">{children}</main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-border-light bg-surface/95 backdrop-blur lg:hidden">
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
