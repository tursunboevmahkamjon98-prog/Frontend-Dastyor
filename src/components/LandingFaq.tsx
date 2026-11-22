"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";




const ITEMS: { q: MessageKey; a: MessageKey }[] = [
  { q: "landing.faq.q1", a: "landing.faq.a1" },
  { q: "landing.faq.q2", a: "landing.faq.a2" },
  { q: "landing.faq.q3", a: "landing.faq.a3" },
  { q: "landing.faq.q4", a: "landing.faq.a4" },
];

export default function LandingFaq() {
  const t = useT();
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-3">
      {ITEMS.map((item, i) => {
        const isOpen = open === i;
        return (
          <div
            key={item.q}
            className={`overflow-hidden rounded-2xl border bg-surface transition-colors ${isOpen ? "border-primary/25 shadow-[0_3px_0_0_var(--color-primary-50),0_16px_28px_-16px_rgba(220,38,38,0.2)]" : "border-border-light shadow-[0_2px_0_0_var(--color-border-light)]"}`}
          >
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : i)}
              className="flex w-full items-center gap-4 px-5 py-4 text-left sm:px-6 sm:py-5"
              aria-expanded={isOpen}
            >
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-colors ${isOpen ? "bg-primary text-white" : "bg-primary-50 text-primary"}`}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="flex-1 text-sm font-semibold text-text-primary sm:text-base">{t(item.q)}</span>
              <ChevronDown
                className={`h-4.5 w-4.5 shrink-0 text-text-tertiary transition-transform duration-300 ${isOpen ? "rotate-180 text-primary" : ""}`}
              />
            </button>
            <div
              className="grid overflow-hidden pl-[3.75rem] pr-5 text-sm leading-relaxed text-text-secondary transition-all duration-300 ease-out sm:pl-[4.25rem] sm:pr-6"
              style={{
                gridTemplateRows: isOpen ? "1fr" : "0fr",
                paddingBottom: isOpen ? "1.1rem" : 0,
                opacity: isOpen ? 1 : 0,
              }}
            >
              <div className="min-h-0">{t(item.a)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
