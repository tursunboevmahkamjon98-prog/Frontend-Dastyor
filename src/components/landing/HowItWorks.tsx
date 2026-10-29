"use client";

import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";
import { STEPS } from "./constants";

/* Deliberately not another row of white cards — everything above and below
 * this section already is one. A plain connected line + nodes reads as a
 * journey instead of three more boxes. */
export default function HowItWorks() {
  const t = useT();

  return (
    <section id="how" className="mx-auto w-full max-w-5xl px-4 pb-16 sm:px-6 sm:pb-24">
      <Reveal className="mx-auto mb-14 max-w-xl text-center">
        <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">{t("landing.how.title")}</h2>
        <p className="mt-3 text-text-secondary">{t("landing.how.subtitle")}</p>
      </Reveal>
      <div className="relative">
        <div
          className="pointer-events-none absolute left-[16%] right-[16%] top-7 hidden h-0.5 bg-gradient-to-r from-primary/15 via-primary to-primary/15 md:block"
          aria-hidden
        />
        <div className="relative grid grid-cols-1 gap-10 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal key={step.n} delay={i * 140} className="flex flex-col items-center text-center">
              <div className="relative z-10 mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_12px_22px_-6px_rgba(220,38,38,0.45)]">
                <step.icon className="h-6 w-6" />
                <span className="absolute -bottom-1.5 -right-1.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-background bg-white text-[11px] font-extrabold text-primary shadow-sm">
                  {step.n}
                </span>
              </div>
              <h3 className="mb-2 font-semibold text-text-primary">{t(step.title)}</h3>
              <p className="max-w-[16rem] text-sm leading-relaxed text-text-secondary">{t(step.desc)}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
