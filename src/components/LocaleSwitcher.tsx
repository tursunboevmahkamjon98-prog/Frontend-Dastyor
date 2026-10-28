"use client";

import { useLocale } from "@/lib/i18n";
import { LOCALES } from "@/lib/messages";




export default function LocaleSwitcher({ className = "" }: { className?: string }) {
  const { locale, setLocale } = useLocale();

  return (
    <div
      className={`inline-flex shrink-0 rounded-xl border border-border-light bg-surface p-0.5 ${className}`}
      role="group"
      aria-label="Language"
    >
      {LOCALES.map(({ code, label, short }) => {
        const active = locale === code;
        return (
          <button
            key={code}
            type="button"
            onClick={() => setLocale(code)}
            aria-pressed={active}
            aria-label={label}
            className={`rounded-[10px] px-2 py-1.5 text-xs font-medium transition sm:px-3 ${
              active
                ? "bg-primary-50 font-semibold text-primary"
                : "text-text-tertiary hover:text-text-primary"
            }`}
          >
            {}
            <span className="sm:hidden">{short}</span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
