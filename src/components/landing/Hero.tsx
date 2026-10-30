"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import Image from "next/image";
import { Sparkles, Check, ArrowRight, Gamepad2 } from "lucide-react";
import { useT } from "@/lib/i18n";
import { SUBJECTS, LANGUAGES } from "@/lib/material-types";
import { FACTS, FEATURES, featureTitleKey } from "./constants";

/* WebGL has no server-side representation, so the card stack loads
 * client-only. The loading placeholder matches the canvas footprint to
 * avoid a layout jump once it mounts. */
const MaterialCards3D = dynamic(() => import("./MaterialCards3D"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-full bg-primary/5" />,
});

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

      <div className="mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-14 pb-10 sm:pt-20 lg:grid-cols-[1.08fr_0.92fr] lg:gap-6">
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary-50 px-3.5 py-1.5 text-xs font-semibold text-primary-dark">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.hero.badge")}
          </div>
          <h1 className="max-w-xl text-4xl font-extrabold tracking-tight text-text-primary sm:text-6xl">
            {t("landing.hero.title")}{" "}
            <span className="relative inline-block whitespace-nowrap">
              <span className="relative bg-gradient-to-r from-primary via-primary-light to-primary bg-clip-text text-transparent">
                {t("landing.hero.titleAccent")}
              </span>
              <svg
                viewBox="0 0 220 14"
                className="pointer-events-none absolute -bottom-2 left-0 h-3 w-full text-primary/70 sm:-bottom-3"
                fill="none"
                aria-hidden
              >
                <path
                  d="M2 9.5C40 2.5 90 1 130 6C160 9.5 190 4 218 7.5"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  style={{ strokeDasharray: 220, animation: "landing-draw 1s ease-out 1.1s both" }}
                />
              </svg>
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

          {/* The right column's full 3D composition only renders at lg+ —
              below that this compact canvas is the only 3D a visitor on a
              phone or a narrow window ever sees. */}
          <div className="relative my-2 h-48 w-48 sm:h-56 sm:w-56 lg:hidden">
            <MaterialCards3D className="h-full w-full" />
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
          <div className="relative mx-auto h-[29rem] w-full max-w-[34rem] [perspective:1200px]">
            <div className="pointer-events-none absolute left-1/2 top-[47%] h-[25rem] w-[25rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/[0.09] blur-3xl" aria-hidden />
            <div className="pointer-events-none absolute bottom-8 left-1/2 h-12 w-[72%] -translate-x-1/2 rounded-[50%] bg-primary/10 blur-2xl" aria-hidden />

            <div className="absolute left-[1%] top-[17%] z-10 w-[49%] rounded-[1.1rem] border border-white bg-white p-1.5 shadow-[0_24px_55px_-20px_rgba(41,19,21,0.38)] sm:p-2" style={{ ["--chip-rot" as string]: "-11deg", animation: "landing-float-chip 6s ease-in-out infinite" }}>
              <Image src="/samples/test/1.png" alt={`${t("landing.samples.exampleAlt")}: ${t("type.test")}`} width={595} height={842} unoptimized className="h-auto w-full rounded-[0.55rem]" />
            </div>

            <div className="absolute right-[1%] top-[21%] z-[5] w-[67%] overflow-hidden rounded-[1.05rem] border border-white bg-white p-1.5 shadow-[0_24px_55px_-20px_rgba(41,19,21,0.34)] sm:p-2" style={{ ["--chip-rot" as string]: "8deg", animation: "landing-float-chip 7s ease-in-out -2s infinite" }}>
              <Image src="/samples/prezentatsiya/1.png" alt={`${t("landing.samples.exampleAlt")}: ${t("type.prezentatsiya")}`} width={1920} height={1080} unoptimized className="h-auto w-full rounded-[0.55rem]" />
            </div>

            <div className="absolute left-[24%] top-[5%] z-20 w-[51%] overflow-hidden rounded-[1.05rem] border border-white bg-white p-1.5 shadow-[0_30px_65px_-18px_rgba(41,19,21,0.4)] sm:p-2" style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out -1s infinite" }}>
              <Image src="/samples/konspekt/1.png" alt={`${t("landing.samples.exampleAlt")}: ${t("type.konspekt")}`} width={595} height={842} unoptimized className="h-auto w-full rounded-[0.55rem]" />
            </div>

            <div
              className="absolute left-0 top-3 z-30 flex items-center gap-1.5 rounded-full border border-border-light bg-white px-3 py-1.5 text-xs font-semibold text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(220,38,38,0.25)]"
              style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
            >
              <Sparkles className="h-3.5 w-3.5" />
              {t("landing.hero.chipAssistant")}
            </div>
            <div
              className="absolute bottom-6 right-0 z-30 rounded-2xl border border-border-light bg-white px-4 py-2.5 text-xs font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(0,0,0,0.12)]"
              style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out infinite", animationDelay: "-2s" }}
            >
              {t("landing.hero.chipTypes")}
            </div>
            <div
              className="absolute right-0 top-[37%] z-30 flex items-center gap-1.5 rounded-2xl border border-border-light bg-white px-3 py-2 text-xs font-semibold text-success shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(5,150,105,0.25)]"
              style={{ ["--chip-rot" as string]: "3deg", animation: "landing-float-chip 4.5s ease-in-out infinite", animationDelay: "-1s" }}
            >
              <Check className="h-3.5 w-3.5" />
              {t("landing.hero.chipReady")}
            </div>
            <div className="absolute bottom-[5%] left-[2%] z-30 w-[52%] max-w-[15rem] rounded-2xl border border-white bg-white p-3 shadow-[0_20px_45px_-16px_rgba(41,19,21,0.3)] sm:p-3.5" style={{ animation: "landing-float 5.8s ease-in-out -2s infinite" }}>
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-igra-bg text-igra-icon">
                  <Gamepad2 className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-[11px] font-bold text-text-primary sm:text-xs">{t("landing.feature.igra.title")}</p>
                  <p className="line-clamp-2 text-[9px] leading-snug text-text-tertiary sm:text-[10px]">{t("landing.feature.igra.desc")}</p>
                </div>
              </div>
              <div className="mt-2.5 grid grid-cols-4 gap-1.5" aria-hidden="true">
                {(["A", "B", "C", "D"] as const).map((answer, index) => (
                  <span key={answer} className={`grid aspect-square place-items-center rounded-lg text-[10px] font-bold ${index === 1 ? "bg-igra-icon text-white shadow-[0_2px_0_0_#5b21b6]" : "border border-igra-icon/15 bg-igra-bg/60 text-igra-icon"}`}>
                    {answer}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
