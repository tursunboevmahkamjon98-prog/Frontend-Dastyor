"use client";

import { useLocale } from "@/lib/i18n";
import { LOCALES } from "@/lib/messages";


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
