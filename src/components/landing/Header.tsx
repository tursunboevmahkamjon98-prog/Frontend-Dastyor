"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import { useT } from "@/lib/i18n";
import { NAV_LINKS } from "./constants";

export default function Header() {
  const t = useT();

  return (
    <header className="sticky top-0 z-30 border-b border-border-light/60 bg-background/75 backdrop-blur-xl">
      <div className="mx-auto grid w-full max-w-[1600px] grid-cols-[1fr_auto] items-center gap-3 px-4 py-3 sm:px-6 md:grid-cols-[auto_1fr] md:gap-x-6 xl:grid-cols-[1fr_auto_1fr] xl:gap-4">
        <Link href="/" className="flex min-w-0 items-center gap-2.5 justify-self-start" aria-label="Dastyor">
          <img src="/brand/dastyor-mark.webp" alt="" className="h-9 w-auto shrink-0" />
          <span className="truncate text-lg font-bold text-text-primary">Dastyor</span>
        </Link>
        <nav className="col-span-2 row-start-2 hidden w-full items-center justify-center gap-0.5 rounded-full border border-white/90 bg-white/55 p-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_8px_24px_-16px_rgba(41,19,21,0.28)] backdrop-blur-xl md:flex xl:col-span-1 xl:row-start-auto xl:w-auto" aria-label={t("landing.nav.home")}>
          <Link
            href="/"
            aria-current="page"
            className="whitespace-nowrap rounded-full bg-primary px-3.5 py-2.5 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark),0_8px_18px_-10px_rgba(220,38,38,0.75)] transition hover:-translate-y-0.5"
          >
            {t("landing.nav.home")}
          </Link>
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="whitespace-nowrap rounded-full px-2.5 py-2.5 text-sm font-medium text-text-secondary transition hover:bg-primary-50 hover:text-primary-dark"
            >
              {t(l.label)}
            </a>
          ))}
        </nav>
        <div className="flex shrink-0 items-center justify-self-end gap-1.5 sm:gap-3">
          <LocaleSwitcher />
          <Link href="/login" className="group hidden items-center gap-2 rounded-full border border-white/90 bg-white/65 py-1.5 pl-4 pr-1.5 text-sm font-semibold text-text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] transition hover:border-primary/20 hover:bg-white sm:inline-flex">
            {t("login.submit")}
            <span className="grid h-8 w-8 place-items-center rounded-full bg-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)] transition group-hover:rotate-45">
              <ArrowUpRight className="h-4 w-4" />
            </span>
          </Link>
          <Link href="/register" className="whitespace-nowrap rounded-full bg-gradient-to-b from-primary-light to-primary px-4 py-2.5 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_4px_0_0_var(--color-primary-dark)] active:translate-y-px active:shadow-[0_1px_0_0_var(--color-primary-dark)] sm:px-5">
            {t("landing.start")}
          </Link>
        </div>
      </div>
    </header>
  );
}
