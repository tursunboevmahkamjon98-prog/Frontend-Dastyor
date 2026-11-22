"use client";

import Link from "next/link";
import Image from "next/image";
import { Sparkles, ArrowRight, Smartphone, Download, Star } from "lucide-react";
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

/* Scattered decorative stars over the gradient — fixed positions/sizes/
 * rotations so they read as a deliberate composition, not randomness.
 * Pure decoration: aria-hidden, no semantic weight. */
const STARS = [
  { top: "3%", left: "16%", size: 30, rotate: -12, opacity: 0.8 },
  { top: "78%", left: "3%", size: 26, rotate: 18, opacity: 0.5 },
  { top: "10%", left: "94%", size: 24, rotate: 25, opacity: 0.75 },
  { top: "55%", left: "97%", size: 18, rotate: -8, opacity: 0.55 },
  { top: "92%", left: "34%", size: 16, rotate: 10, opacity: 0.4 },
] as const;

export default function Hero({ apkSize }: { apkSize: string | null }) {
  const t = useT();

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary-dark via-primary to-orange-500">
      {STARS.map((s, i) => (
        <Star
          key={i}
          className="pointer-events-none absolute -z-0 fill-white text-white"
          style={{
            top: s.top, left: s.left, width: s.size, height: s.size,
            opacity: s.opacity, transform: `rotate(${s.rotate}deg)`,
            animation: `landing-sparkle-twinkle ${4 + i}s ease-in-out infinite`,
            animationDelay: `-${i * 0.7}s`,
          }}
          aria-hidden
        />
      ))}
      <div
        className="pointer-events-none absolute left-1/2 top-0 -z-0 h-[620px] w-[920px] -translate-x-1/2 rounded-full bg-white/[0.08] blur-3xl"
        style={{ animation: "landing-blob-drift 16s ease-in-out infinite" }}
        aria-hidden
      />

      <div className="relative mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-10 pb-10 sm:pt-14 lg:grid-cols-[1.08fr_0.92fr] lg:items-start lg:gap-6">
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 px-3.5 py-1.5 text-xs font-semibold text-white backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.hero.badge")}
          </div>
          <h1 className="max-w-2xl font-extrabold tracking-tight text-white">
            <span className="block text-3xl leading-[1.08] sm:text-5xl lg:text-6xl">
              {t("landing.hero.title")}
            </span>
            <span className="mt-3 inline-flex -rotate-1 items-center gap-2 rounded-2xl bg-white px-3.5 py-1.5 text-2xl leading-none text-primary shadow-[0_6px_0_0_rgba(0,0,0,0.12)] sm:mt-4 sm:gap-2.5 sm:rounded-[1.1rem] sm:px-5 sm:py-2.5 sm:text-4xl lg:text-5xl">
              <Sparkles className="h-5 w-5 shrink-0 sm:h-8 sm:w-8 lg:h-9 lg:w-9" />
              {t("landing.hero.titleAccent")}
            </span>
          </h1>
          <p className="mt-4 max-w-xl text-sm text-white/85 sm:text-base">
            {t("landing.hero.subtitle")}
          </p>

          <div className="mt-6 flex max-w-xl flex-wrap justify-center gap-2 lg:justify-start">
            {FEATURES.filter(({ id }) => id === "konspekt" || id === "test" || id === "prezentatsiya" || id === "igra").map(({ id, icon: Icon, bg, color }) => (
              <span key={id} className={`inline-flex items-center gap-1.5 rounded-full border border-white/80 px-3 py-1.5 text-xs font-semibold shadow-[0_2px_0_0_rgba(0,0,0,0.1)] ${bg} ${color}`}>
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {t(featureTitleKey(id))}
              </span>
            ))}
          </div>

          {/* The right column's full illustration only shows at lg+ —
              below that this smaller teacher is what a phone or narrow
              window visitor sees. */}
          <div className="relative my-2 flex h-40 items-center justify-center sm:h-48 lg:hidden">
            <Image src="/hero/team-sticker.png" alt="" width={699} height={526} priority className="h-full w-auto object-contain drop-shadow-[0_14px_20px_rgba(0,0,0,0.25)]" />
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/register"
              className="group flex items-center justify-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-primary shadow-[0_4px_0_0_rgba(0,0,0,0.15)] transition-all duration-150 hover:-translate-y-0.5 active:translate-y-0.5"
            >
              {t("landing.hero.ctaPrimary")}
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/login"
              className="rounded-xl border border-white/40 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:-translate-y-0.5 hover:bg-white/10 active:translate-y-0.5"
            >
              {t("landing.hero.ctaSecondary")}
            </Link>
          </div>

          {/* Direct APK download: the app is not on Google Play, so this is the
              install path. The file lives in public/ so the same deploy that
              ships the code ships the APK. */}
          <a
            href="/dastyor.apk"
            download
            className="group relative mt-5 inline-flex items-center gap-3 overflow-hidden rounded-2xl bg-text-primary px-5 py-3 text-left shadow-[0_4px_0_0_rgba(0,0,0,0.35),0_14px_28px_-10px_rgba(41,19,21,0.45)] transition-all duration-150 hover:-translate-y-0.5 active:translate-y-0.5"
          >
            <span
              className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 -skew-x-12 bg-white/10 transition-transform duration-700 group-hover:translate-x-[350%]"
              aria-hidden
            />
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/25">
              <Smartphone className="h-5 w-5 text-primary-light" />
            </span>
            <span className="leading-tight">
              <span className="block text-[11px] font-medium text-white/60">{t("landing.hero.apkTitle")}</span>
              <span className="flex items-center gap-1.5 text-sm font-bold text-white">
                rahnamo.apk
                {apkSize && <span className="font-normal text-white/55">· {apkSize} {t("landing.hero.apkMb")}</span>}
              </span>
            </span>
            <Download className="ml-1 h-4 w-4 shrink-0 text-white/70 transition group-hover:translate-y-0.5" />
          </a>
          <p className="mt-2 text-xs text-white/60">{t("landing.hero.apkNote")}</p>

          {/* Inline stats — a slim row of numbers, not boxed cards, so the
              hero reads as one composition instead of hero + a stats
              section stacked under it. */}
          <div className="mt-9 flex items-center gap-5 divide-x divide-white/20 sm:gap-7">
            {STATS.map((s, i) => (
              <div key={s.key} className={i === 0 ? "" : "pl-5 sm:pl-7"}>
                <p className="text-2xl font-extrabold text-white sm:text-3xl">{s.value}</p>
                <p className="text-[11px] font-medium text-white/70 sm:text-xs">{t(s.key)}</p>
              </div>
            ))}
          </div>

          <div className="mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 lg:justify-start">
            {FACTS.map(({ icon: Icon, key }) => (
              <span key={key} className="flex items-center gap-1.5 text-sm text-white/80">
                <Icon className="h-4 w-4 text-white" />
                {t(key)}
              </span>
            ))}
          </div>
        </div>

        <div className="relative hidden lg:block">
          <div
            className="pointer-events-none absolute right-10 top-6 h-56 w-56 rounded-full bg-white/[0.14] blur-3xl"
            style={{ animation: "landing-blob-drift 14s ease-in-out infinite" }}
            aria-hidden
          />
          <div
            className="pointer-events-none absolute bottom-0 left-6 h-48 w-48 rounded-full bg-white/[0.10] blur-3xl"
            style={{ animation: "landing-blob-drift 17s ease-in-out infinite", animationDelay: "-6s" }}
            aria-hidden
          />
          <TeacherStage />
        </div>
      </div>
    </section>
  );
}
