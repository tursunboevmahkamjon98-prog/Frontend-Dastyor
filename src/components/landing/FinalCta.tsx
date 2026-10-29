"use client";

import Link from "next/link";
import { Languages, ArrowRight } from "lucide-react";
import Reveal from "@/components/Reveal";
import { useT } from "@/lib/i18n";

/* Full-bleed red band to close the page — every section above is a white
 * card on a near-white background, so the strongest possible contrast for
 * the last thing a visitor sees is to invert that, not add one more white
 * card with a red button. */
export default function FinalCta() {
  const t = useT();

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-light via-primary to-primary-dark py-20 text-center sm:py-28">
      <div
        className="pointer-events-none absolute -left-20 top-0 h-80 w-80 rounded-full bg-white/10 blur-3xl"
        style={{ animation: "landing-blob-drift 18s ease-in-out infinite" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 bottom-0 h-72 w-72 rounded-full bg-black/10 blur-3xl"
        style={{ animation: "landing-blob-drift 22s ease-in-out infinite", animationDelay: "-5s" }}
        aria-hidden
      />
      <div className="relative mx-auto max-w-2xl px-4">
        <Reveal>
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-white">
            <Languages className="h-3.5 w-3.5" />
            {t("landing.cta.langs")}
          </div>
          <h2 className="mb-3 text-2xl font-bold text-white sm:text-3xl">{t("landing.cta.title")}</h2>
          <p className="mb-7 text-white/80">{t("landing.cta.subtitle")}</p>
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 rounded-xl bg-white px-8 py-3.5 text-sm font-semibold text-primary-dark shadow-[0_4px_0_0_rgba(0,0,0,0.15),0_14px_28px_-6px_rgba(0,0,0,0.3)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_rgba(0,0,0,0.15),0_18px_32px_-6px_rgba(0,0,0,0.35)] active:translate-y-0.5 active:shadow-[0_1px_0_0_rgba(0,0,0,0.15)]"
          >
            {t("landing.cta.button")}
            <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
          </Link>
        </Reveal>
      </div>
    </section>
  );
}
