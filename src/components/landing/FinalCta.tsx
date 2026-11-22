"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";
import { SUBJECTS, LANGUAGES } from "@/lib/material-types";
import { FEATURES } from "./constants";

const STATS = [
  { value: String(FEATURES.length), key: "landing.stat.types" },
  { value: String(SUBJECTS.length), key: "landing.stat.subjects" },
  { value: String(LANGUAGES.length), key: "landing.stat.languages" },
] as const;

/* Full-bleed red band to close the page — every section above is a white
 * card on a near-white background, so the strongest possible contrast for
 * the last thing a visitor sees is to invert that, not add one more white
 * card with a red button. Built up with a badge, a bigger headline and a
 * stat row so it carries real weight instead of just text + a button. */
export default function FinalCta() {
  const t = useT();

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-light via-primary to-primary-dark py-24 text-center sm:py-32">
      <div
        className="pointer-events-none absolute -left-20 top-0 h-96 w-96 rounded-full bg-white/10 blur-3xl"
        style={{ animation: "landing-blob-drift 18s ease-in-out infinite" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 bottom-0 h-80 w-80 rounded-full bg-black/10 blur-3xl"
        style={{ animation: "landing-blob-drift 22s ease-in-out infinite", animationDelay: "-5s" }}
        aria-hidden
      />
      <div className="relative mx-auto max-w-2xl px-4">
        <Reveal>
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 px-3.5 py-1.5 text-xs font-semibold text-white backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.hero.badge")}
          </div>
          <h2 className="mb-4 text-3xl font-extrabold leading-tight text-white sm:text-4xl lg:text-5xl">{t("landing.cta.title")}</h2>
          <p className="mb-8 text-base text-white/80 sm:text-lg">{t("landing.cta.subtitle")}</p>
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 rounded-xl bg-white px-8 py-3.5 text-sm font-semibold text-primary-dark shadow-[0_4px_0_0_rgba(0,0,0,0.15),0_14px_28px_-6px_rgba(0,0,0,0.3)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_rgba(0,0,0,0.15),0_18px_32px_-6px_rgba(0,0,0,0.35)] active:translate-y-0.5 active:shadow-[0_1px_0_0_rgba(0,0,0,0.15)]"
          >
            {t("landing.cta.button")}
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </Link>

          <div className="mx-auto mt-12 flex max-w-md items-center justify-center gap-6 divide-x divide-white/20 border-t border-white/15 pt-8 sm:gap-10">
            {STATS.map((s, i) => (
              <div key={s.key} className={i === 0 ? "" : "pl-6 sm:pl-10"}>
                <p className="text-2xl font-extrabold text-white sm:text-3xl">{s.value}</p>
                <p className="text-[11px] font-medium text-white/70 sm:text-xs">{t(s.key)}</p>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
