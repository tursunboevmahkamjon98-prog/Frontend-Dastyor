"use client";

import { useT } from "@/lib/i18n";
import { NAV_LINKS } from "./constants";

export default function Footer() {
  const t = useT();

  return (
    <footer className="border-t border-border-light py-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-4 px-4 text-center sm:flex-row sm:justify-between sm:text-left">
        <div className="flex items-center gap-2">
          <img src="/brand/dastyor-mark.webp" alt="Dastyor" className="h-7 w-auto" />
          <span className="text-sm font-semibold text-text-primary">Dastyor</span>
        </div>
        <nav className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className="text-xs font-medium text-text-secondary hover:text-primary">
              {t(l.label)}
            </a>
          ))}
        </nav>
        <p className="text-xs text-text-tertiary">© {new Date().getFullYear()} Dastyor. {t("landing.footer.rights")}</p>
      </div>
    </footer>
  );
}
