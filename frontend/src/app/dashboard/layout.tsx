"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Menu, Plus, WifiOff, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useOnlineStatus } from "@/lib/use-online-status";
import { markBackNavigationListener } from "@/lib/back-navigation";
import { API_ORIGIN } from "@/lib/api";
import { useT, useAccountLocale } from "@/lib/i18n";
import { CREATE_HREF, NAV_ITEMS, TAB_ITEMS, isActive, pageTitleKey } from "@/lib/dashboard-nav";
import AppUpdateBanner from "@/components/AppUpdateBanner";
import ThemeToggle from "@/components/ThemeToggle";
import { LogoMark } from "@/components/Logo";
import IconRail from "@/components/dashboard/IconRail";
import GlobalSearch from "@/components/dashboard/GlobalSearch";
import HeaderActions from "@/components/dashboard/HeaderActions";

/* Shared workspace shell: labelled desktop navigation and a compact mobile
 * dock use the same destinations and brand as the dashboard composer. */

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  const t = useT();
  const { user, loading } = useAuth();
  useAccountLocale(user?.language);
  const router = useRouter();
  const pathname = usePathname();
  const online = useOnlineStatus();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => markBackNavigationListener(), []);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-meta text-text-tertiary">{t("common.loading")}</p>
      </div>
    );
  }

  const avatar = user.avatar_url ? `${API_ORIGIN}${user.avatar_url}` : null;
  const initial = user.full_name.trim().charAt(0).toUpperCase();
  const creating = pathname.startsWith(CREATE_HREF);

  const avatarNode = avatar ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={avatar} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover" />
  ) : (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-50 text-meta font-semibold text-primary-accent">
      {initial}
    </span>
  );

  return (
    <div className="workspace-shell min-h-screen bg-background">
      {!online && (
        <div className="sticky top-0 z-40 flex items-center justify-center gap-2 bg-text-primary px-4 py-2 text-center text-meta font-medium text-background">
          <WifiOff className="h-4 w-4 shrink-0" />
          {t("common.offline")}
        </div>
      )}

      <AppUpdateBanner />

      <IconRail pathname={pathname} avatarNode={avatarNode} />

      <div className="lg:pl-56">
        {/* ---- Header (desktop) --------------------------------------- */}
        <header className="sticky top-0 z-30 hidden h-20 items-center gap-5 border-b border-border bg-surface/95 px-7 backdrop-blur lg:flex">
          <span className="shrink-0 text-xl font-semibold tracking-tight text-text-primary">{t(pageTitleKey(pathname))}</span>
          <GlobalSearch className="ml-auto w-full max-w-xs" />
          <HeaderActions name={user.full_name} balance={user.balance_somoni} avatarNode={avatarNode} pathname={pathname} />
        </header>

        {/* ---- App bar (mobile) ------------------------------------- */}
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border-light bg-surface/90 px-4 py-2.5 backdrop-blur lg:hidden">
          <button type="button" onClick={() => setMenuOpen(true)} aria-label={t("nav.openMenu")} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-text-primary hover:bg-surface-muted"><Menu className="h-5 w-5" /></button>
          <Link href="/dashboard" aria-label="Dastyor" className="shrink-0">
            <LogoMark height="1.75rem" alt="Dastyor" />
          </Link>
          <span className="hidden truncate text-subheading font-semibold text-text-primary sm:block">
            {t(pageTitleKey(pathname))}
          </span>
          <div className="ml-auto"><HeaderActions name={user.full_name} balance={user.balance_somoni} avatarNode={avatarNode} pathname={pathname} /></div>
        </header>

        {menuOpen && <div className="fixed inset-0 z-50 bg-text-primary/30 lg:hidden" onClick={() => setMenuOpen(false)}>
          <aside className="flex h-full w-64 max-w-[85vw] flex-col bg-surface p-4 shadow-float" onClick={(event) => event.stopPropagation()}>
            <div className="mb-6 flex items-center justify-between"><Link href="/dashboard" onClick={() => setMenuOpen(false)}><LogoMark height="2rem" alt="Dastyor" /></Link>
              <button type="button" onClick={() => setMenuOpen(false)} aria-label={t("nav.closeMenu")} className="rounded-lg p-2 text-text-secondary"><X className="h-5 w-5" /></button></div>
            <nav className="flex flex-col gap-1" aria-label={t("nav.groupMain")}>
              {[...NAV_ITEMS.slice(0, 2), { href: CREATE_HREF, labelKey: "nav.create" as const, icon: Plus }, ...NAV_ITEMS.slice(2)].map(({ href, labelKey, icon: Icon }) =>
                <Link key={href} href={href} onClick={() => setMenuOpen(false)} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-text-primary hover:bg-primary-50 hover:text-primary-accent"><Icon className="h-5 w-5" />{t(labelKey)}</Link>)}
            </nav>
            <div className="mt-auto"><ThemeToggle /></div>
          </aside>
        </div>}

        <main className="pb-28 lg:pb-16">{children}</main>
      </div>

      {/* ---- Mobile workspace dock ------------------------------------ */}
      <nav aria-label={t("nav.groupMain")} className="fixed inset-x-0 bottom-0 z-30 border-t border-border-light bg-surface/95 px-2 pb-[env(safe-area-inset-bottom)] shadow-float backdrop-blur lg:hidden">
        <div className="mx-auto grid max-w-lg grid-cols-5 items-end gap-1 py-2">
          {TAB_ITEMS.slice(0, 2).map((item) => (
            <Tab key={item.href} item={item} pathname={pathname} />
          ))}

          <Link
            href={CREATE_HREF}
            aria-label={t("nav.create")}
            aria-current={creating ? "page" : undefined}
            className="flex min-w-0 flex-col items-center gap-1"
          >
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-control text-white transition-colors duration-150 ${
                creating ? "bg-primary-dark" : "bg-primary"
              }`}
            >
              <Plus className="h-4 w-4" strokeWidth={2.5} />
            </span>
            <span className="max-w-full truncate text-[10px] font-semibold text-primary-accent">{t("nav.create")}</span>
          </Link>

          {TAB_ITEMS.slice(2, 4).map((item) => (
            <Tab key={item.href} item={item} pathname={pathname} />
          ))}
        </div>
      </nav>
    </div>
  );
}

function Tab({
  item,
  pathname,
}: {
  item: (typeof TAB_ITEMS)[number];
  pathname: string;
}) {
  const t = useT();
  const { href, labelKey, icon: Icon, exact } = item;
  const active = isActive(pathname, href, exact);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      aria-label={t(labelKey)}
      title={t(labelKey)}
      className={`flex min-w-0 flex-col items-center gap-1 transition-colors duration-150 ${
        active ? "text-primary-accent" : "text-text-tertiary"
      }`}
    >
      <span className={active ? "flex h-9 w-9 items-center justify-center rounded-control bg-primary-50" : "flex h-9 w-9 items-center justify-center"}>
        <Icon className="h-4.5 w-4.5" strokeWidth={active ? 2.4 : 1.9} />
      </span>
      <span className="max-w-full truncate text-[10px] font-medium">{t(labelKey)}</span>
    </Link>
  );
}
