"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { useAuth } from "@/lib/auth-context";
import { materialsApi, DashboardStats, SearchResultItem } from "@/lib/api";
import { useLocale } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";
import HeroCompose from "@/components/dashboard/HeroCompose";
import QuickStats from "@/components/dashboard/QuickStats";
import RecentList, { type LoadState } from "@/components/dashboard/RecentList";

const RECENT_LIMIT = 6;

function greetingKey(): MessageKey {
  const h = new Date().getHours();
  if (h < 5) return "home.greetNight";
  if (h < 12) return "home.greetMorning";
  if (h < 18) return "home.greetDay";
  return "home.greetEvening";
}

const LOCALE_TAG: Record<string, string> = { ru: "ru-RU", tg: "tg-TJ", en: "en-GB" };

export default function DashboardHome() {
  const { locale, t } = useLocale();
  const { user } = useAuth();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<SearchResultItem[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  /* Bumping this re-runs the effect. The alternative — a load() the effect
   * and the retry button both call — puts a synchronous setState in the
   * effect body, which is the cascading-render pattern the lint rule here
   * rejects. Every setState below happens in a promise callback or an
   * event handler instead. */
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    materialsApi
      .stats()
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch(() => {});

    materialsApi
      .search("")
      .then((items) => {
        if (cancelled) return;
        setRecent(items.filter((i) => i.type !== "igra").slice(0, RECENT_LIMIT));
        setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setState("loading");
    setAttempt((n) => n + 1);
  }, []);

  const firstName = user?.full_name?.trim().split(/\s+/)[0] ?? "";
  const today = new Date().toLocaleDateString(LOCALE_TAG[locale] ?? "ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const total = stats
    ? stats.konspekt_count +
      stats.lecture_count +
      stats.test_count +
      stats.presentation_count +
      stats.practical_count
    : null;

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 pb-12 pt-7 sm:px-7 lg:px-10 lg:pb-16 lg:pt-10">
      <header className="soft-dashboard-welcome relative mb-7 flex min-h-48 items-center justify-between gap-4 overflow-hidden rounded-[1.75rem] border px-5 py-5 shadow-card sm:min-h-56 sm:px-7 lg:px-9">
        <div className="relative z-10 min-w-0 flex-1 sm:pr-52 lg:pr-[22rem]">
          <p className="text-micro font-semibold uppercase tracking-[0.14em] text-secondary-accent">{today}</p>
          <h1 className="mt-2 break-words text-[clamp(1.6rem,4vw,2.7rem)] font-semibold leading-tight tracking-tight text-text-primary">
            {t(greetingKey())}{firstName && `, ${firstName}`}
          </h1>
          <p className="mt-1.5 max-w-xl text-sm text-text-secondary sm:text-base">{t("home.prompt")}</p>
          <div className="mt-4"><QuickStats total={total} /></div>
        </div>
        <Image
          src="/soft3d/book.webp"
          alt=""
          aria-hidden="true"
          width={300}
          height={300}
          className="soft3d-float-prop pointer-events-none absolute right-[15%] top-[8%] z-0 hidden h-14 w-14 object-contain opacity-90 sm:block lg:h-20 lg:w-20"
          style={{ ["--chip-rot" as string]: "-9deg", ["--float-duration" as string]: "5.8s", ["--float-delay" as string]: "0.2s" }}
        />
        <div className="soft3d-welcome-art pointer-events-none absolute -right-3 bottom-[-3.75rem] hidden sm:block lg:right-3 lg:bottom-[-4.5rem]">
          <Image src="/soft3d/teacher-hero.webp" alt="" aria-hidden="true" width={768} height={512} priority className="h-auto w-72 object-contain drop-shadow-[0_18px_22px_rgba(70,48,45,0.16)] sm:w-[20rem] lg:w-[25rem]" />
        </div>
      </header>

      <HeroCompose />

      <div className="mt-10">
        <RecentList state={state} items={recent} onRetry={retry} />
      </div>
    </div>
  );
}
