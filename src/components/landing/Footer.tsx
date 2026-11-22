"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";
import { NAV_LINKS } from "./constants";

export default function Footer() {
  const t = useT();

  return (
    <footer className="border-t border-border-light bg-surface-muted/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-1">
            <div className="mb-3 flex items-center gap-2">
              <img src="/brand/rahnamo-mark-tight.png" alt="" className="h-8 w-auto" />
              <span className="text-sm font-bold text-text-primary">Rahnamo</span>
            </div>
            <p className="max-w-xs text-sm leading-relaxed text-text-tertiary">{t("landing.footer.tagline")}</p>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-text-tertiary">{t("landing.footer.product")}</h3>
            <nav className="flex flex-col gap-2.5">
              <Link href="/" className="text-sm font-medium text-text-secondary hover:text-primary">{t("landing.nav.home")}</Link>
              {NAV_LINKS.map((l) => (
                <a key={l.href} href={l.href} className="text-sm font-medium text-text-secondary hover:text-primary">
                  {t(l.label)}
                </a>
              ))}
            </nav>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-text-tertiary">{t("landing.footer.account")}</h3>
            <nav className="flex flex-col gap-2.5">
              <Link href="/login" className="text-sm font-medium text-text-secondary hover:text-primary">{t("login.submit")}</Link>
              <Link href="/register" className="text-sm font-medium text-text-secondary hover:text-primary">{t("landing.start")}</Link>
            </nav>
          </div>

          <div>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-text-tertiary">{t("landing.footer.legal")}</h3>
            <nav className="flex flex-col gap-2.5">
              <Link href="/privacy" className="text-sm font-medium text-text-secondary hover:text-primary">{t("landing.footer.privacy")}</Link>
              <Link href="/terms" className="text-sm font-medium text-text-secondary hover:text-primary">{t("landing.footer.terms")}</Link>
            </nav>
          </div>
        </div>

        <div className="mt-10 border-t border-border-light pt-6 text-center text-xs text-text-tertiary sm:text-left">
          © {new Date().getFullYear()} Rahnamo. {t("landing.footer.rights")}
        </div>
      </div>
    </footer>
  );
}
