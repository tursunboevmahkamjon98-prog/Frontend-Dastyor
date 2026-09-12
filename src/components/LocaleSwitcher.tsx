"use client";

import { useLocale } from "@/lib/i18n";
import { LOCALES } from "@/lib/messages";

/** Three-way segmented control for the UI language.
 *
 * Sits on the auth pages because that is the one place a visitor has to be
 * able to change language *before* signing in — a Tajik teacher landing on
 * a Russian login form otherwise has no way through to the setting, which
 * lives behind the account. */
export default function LocaleSwitcher({ className = "" }: { className?: string }) {
  const { locale, setLocale } = useLocale();

  return (
    <div
      className={`inline-flex rounded-xl border border-border-light bg-surface p-0.5 ${className}`}
      role="group"
      aria-label="Language"
    >
      {LOCALES.map(({ code, label }) => {
        const active = locale === code;
        return (
          <button
            key={code}
            type="button"
            onClick={() => setLocale(code)}
            aria-pressed={active}
            className={`rounded-[10px] px-3 py-1.5 text-xs font-medium transition ${
              active
                ? "bg-primary-50 font-semibold text-primary"
                : "text-text-tertiary hover:text-text-primary"
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
