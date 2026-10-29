"use client";

import Link from "next/link";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import { useT } from "@/lib/i18n";
import { NAV_LINKS } from "./constants";

export default function Header() {
  const t = useT();

  return (
    <header className="sticky top-0 z-30 border-b border-border-light/70 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-2.5">
          <img src="/brand/dastyor-mark.webp" alt="Dastyor" className="h-9 w-auto shrink-0" />
          <span className="truncate text-lg font-bold text-text-primary">Dastyor</span>
        </div>
        <nav className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-text-secondary transition hover:bg-surface-muted hover:text-text-primary"
            >
              {t(l.label)}
            </a>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-3">
          <LocaleSwitcher />
          <Link href="/login" className="hidden rounded-xl px-3 py-2 text-sm font-semibold text-text-primary hover:bg-surface-muted sm:inline-block sm:px-4">
            {t("login.submit")}
          </Link>
          <Link href="/register" className="whitespace-nowrap rounded-xl bg-gradient-to-b from-primary-light to-primary px-3 py-2 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_4px_0_0_var(--color-primary-dark)] active:translate-y-px active:shadow-[0_1px_0_0_var(--color-primary-dark)] sm:px-4">
            {t("landing.start")}
          </Link>
        </div>
      </div>
    </header>
  );
}
