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
    <div className="mx-auto max-w-3xl divide-y divide-border-light rounded-3xl border border-border-light bg-surface">
      {ITEMS.map((item, i) => {
        const isOpen = open === i;
        return (
          <div key={item.q}>
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : i)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left sm:px-6"
              aria-expanded={isOpen}
            >
              <span className="text-sm font-semibold text-text-primary sm:text-base">{t(item.q)}</span>
              <ChevronDown
                className={`h-4.5 w-4.5 shrink-0 text-text-tertiary transition-transform duration-300 ${isOpen ? "rotate-180 text-primary" : ""}`}
              />
            </button>
            <div
              className="grid overflow-hidden px-5 text-sm leading-relaxed text-text-secondary transition-all duration-300 ease-out sm:px-6"
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
