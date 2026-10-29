"use client";

import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";
import { TRUST } from "./constants";

/* One strip, not four separate shadowed cards — the repetition of
 * Features/Stats/HowItWorks boxes is exactly what read as "same section
 * five times" before. */
export default function Trust() {
  const t = useT();

  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
      <Reveal className="mx-auto mb-10 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.trust.title")}</h2>
        <p className="mt-3 text-text-secondary">{t("landing.trust.subtitle")}</p>
      </Reveal>
      <Reveal className="overflow-hidden rounded-2xl border border-border-light bg-white shadow-[0_3px_0_0_var(--color-border-light),0_14px_28px_-10px_rgba(0,0,0,0.08)]">
        <div className="flex flex-col divide-y divide-border-light sm:flex-row sm:divide-x sm:divide-y-0">
          {TRUST.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex flex-1 items-center gap-3 px-6 py-5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-50">
                <Icon className="h-5 w-5 text-primary" />
              </span>
              <div className="text-left">
                <p className="text-sm font-semibold leading-tight text-text-primary">{t(title)}</p>
                <p className="text-xs leading-snug text-text-secondary">{t(desc)}</p>
              </div>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
