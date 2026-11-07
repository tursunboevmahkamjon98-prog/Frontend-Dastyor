"use client";

import Link from "next/link";
import Image from "next/image";
import { Sparkles, ArrowRight } from "lucide-react";
import { useT } from "@/lib/i18n";
import { SUBJECTS, LANGUAGES } from "@/lib/material-types";
import TeacherStage from "./TeacherStage";
import { FACTS, FEATURES, featureTitleKey } from "./constants";

const STATS = [
  { value: String(FEATURES.length), key: "landing.stat.types" },
  { value: String(SUBJECTS.length), key: "landing.stat.subjects" },
  { value: String(LANGUAGES.length), key: "landing.stat.languages" },
  { value: "4", key: "landing.stat.formats" },
] as const;

export default function Hero() {
  const t = useT();

  return (
    <section className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[620px] w-[920px] -translate-x-1/2 rounded-full bg-primary/[0.10] blur-3xl"
        style={{ animation: "landing-blob-drift 16s ease-in-out infinite" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-24 top-24 -z-10 h-72 w-72 rounded-full bg-pres-icon/[0.08] blur-3xl"
        style={{ animation: "landing-blob-drift 20s ease-in-out infinite", animationDelay: "-4s" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-24 top-60 -z-10 h-72 w-72 rounded-full bg-note-icon/[0.08] blur-3xl"
        style={{ animation: "landing-blob-drift 18s ease-in-out infinite", animationDelay: "-9s" }}
        aria-hidden
      />

      <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-14 pb-10 sm:pt-20 lg:grid-cols-[1.08fr_0.92fr] lg:items-start lg:gap-6">
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.hero.badge")}
          </div>
          <h1 className="max-w-3xl font-extrabold tracking-tight text-text-primary">
            <span className="block text-4xl leading-[1.04] sm:text-6xl lg:text-7xl">
              {t("landing.hero.title")}
            </span>
            <span className="mt-3 inline-flex -rotate-1 items-center gap-2 rounded-2xl border border-primary/15 bg-white px-4 py-2 text-3xl leading-none text-primary shadow-[0_5px_0_0_var(--color-border-light),0_14px_26px_-12px_rgba(220,38,38,0.28)] sm:mt-4 sm:gap-3 sm:rounded-[1.35rem] sm:px-6 sm:py-3 sm:text-5xl lg:text-6xl">
              <Sparkles className="h-7 w-7 shrink-0 sm:h-10 sm:w-10 lg:h-11 lg:w-11" />
              {t("landing.hero.titleAccent")}
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-base text-text-secondary sm:text-lg">
            {t("landing.hero.subtitle")}
          </p>

          <div className="mt-6 flex max-w-xl flex-wrap justify-center gap-2 lg:justify-start">
            {FEATURES.filter(({ id }) => id === "konspekt" || id === "test" || id === "prezentatsiya" || id === "igra").map(({ id, icon: Icon, bg, color }) => (
              <span key={id} className={`inline-flex items-center gap-1.5 rounded-full border border-white/80 px-3 py-1.5 text-xs font-semibold shadow-[0_2px_0_0_var(--color-border-light)] ${bg} ${color}`}>
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {t(featureTitleKey(id))}
              </span>
            ))}
          </div>

          {/* The right column's full illustration only shows at lg+ —
              below that this smaller teacher is what a phone or narrow
              window visitor sees. */}
          <div className="relative my-2 flex h-48 items-center justify-center sm:h-56 lg:hidden">
            <Image src="/hero/teacher.png" alt="" width={443} height={484} priority className="h-full w-auto object-contain" />
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/register"
              className="group flex items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary px-6 py-3 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_10px_24px_-6px_rgba(220,38,38,0.45)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_14px_28px_-6px_rgba(220,38,38,0.5)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark),0_4px_10px_-4px_rgba(220,38,38,0.4)]"
            >
              {t("landing.hero.ctaPrimary")}
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/login"
              className="rounded-xl border border-border bg-white px-6 py-3 text-sm font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border),0_8px_16px_-6px_rgba(0,0,0,0.08)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_4px_0_0_var(--color-border),0_10px_20px_-6px_rgba(0,0,0,0.1)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-border)]"
            >
              {t("landing.hero.ctaSecondary")}
            </Link>
          </div>

          {/* Inline stats — a slim row of numbers, not boxed cards, so the
              hero reads as one composition instead of hero + a stats
              section stacked under it. */}
          <div className="mt-9 flex items-center gap-5 divide-x divide-border-light sm:gap-7">
            {STATS.map((s, i) => (
              <div key={s.key} className={i === 0 ? "" : "pl-5 sm:pl-7"}>
                <p className="text-2xl font-extrabold text-primary sm:text-3xl">{s.value}</p>
                <p className="text-[11px] font-medium text-text-tertiary sm:text-xs">{t(s.key)}</p>
              </div>
            ))}
          </div>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-start">
            {FACTS.map(({ icon: Icon, key }) => (
              <span key={key} className="flex items-center gap-1.5 text-sm text-text-tertiary">
                <Icon className="h-4 w-4 text-primary" />
                {t(key)}
              </span>
            ))}
          </div>
        </div>

        <div className="relative hidden lg:block">
          <div
            className="pointer-events-none absolute right-10 top-6 h-56 w-56 rounded-full bg-primary/[0.14] blur-3xl"
            style={{ animation: "landing-blob-drift 14s ease-in-out infinite" }}
            aria-hidden
          />
          <div
            className="pointer-events-none absolute bottom-0 left-6 h-48 w-48 rounded-full bg-note-icon/[0.10] blur-3xl"
            style={{ animation: "landing-blob-drift 17s ease-in-out infinite", animationDelay: "-6s" }}
            aria-hidden
          />
          <TeacherStage />
        </div>
      </div>
    </section>
  );
}
