"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Layers, ChevronRight, Clock, Sparkles, Gift, ArrowRight } from "lucide-react";
import { materialsApi, billingApi, DashboardStats, SearchResultItem, PromoBanner } from "@/lib/api";
import { MATERIAL_TYPE_CONFIG, LIBRARY_TYPES, CREATABLE_TYPES, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import Reveal from "@/components/Reveal";

const STAT_KEYS: Record<(typeof LIBRARY_TYPES)[number], keyof DashboardStats> = {
  konspekt: "konspekt_count",
  lektsiya: "lecture_count",
  test: "test_count",
  prezentatsiya: "presentation_count",
  amaliy: "practical_count",
};

/* Literal class names, not `color.replace("text-", "bg-")` — Tailwind's
 * build-time scanner only emits utilities it finds as literal strings in
 * source, so a runtime-constructed class name silently renders nothing for
 * any token that doesn't already appear literally somewhere else. */
const STAT_BAR_FILL: Record<(typeof LIBRARY_TYPES)[number], string> = {
  konspekt: "bg-note-icon",
  lektsiya: "bg-lecture-icon",
  test: "bg-test-icon",
  prezentatsiya: "bg-pres-icon",
  amaliy: "bg-amaliy-icon",
};

export default function DashboardHome() {
  const t = useT();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<SearchResultItem[]>([]);
  const [banner, setBanner] = useState<PromoBanner | null>(null);

  useEffect(() => {
    materialsApi.stats().then(setStats).catch(() => {});
    materialsApi
      .search("")
      .then((items) => setRecent(items.filter((i) => i.type !== "igra").slice(0, 4)))
      .catch(() => {});
    billingApi.promoBanner().then(setBanner).catch(() => {});
  }, []);

  const maxCount = stats ? Math.max(1, ...LIBRARY_TYPES.map((type) => stats[STAT_KEYS[type]])) : 1;
  const { icon: GameIcon, bg: gameBg, color: gameColor } = MATERIAL_TYPE_CONFIG.igra;

  return (
    <div className="mx-auto max-w-3xl px-4 pt-1 sm:px-6 lg:max-w-6xl lg:px-8 lg:pt-8">
      {}
      <div className="mb-8 pt-4 lg:pt-0">
        <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
          <Sparkles className="h-3.5 w-3.5" />
          {t("home.quickCreate")}
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {CREATABLE_TYPES.map((type) => {
            const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
            const label = t(MATERIAL_TYPE_LABEL_KEY[type]);
            return (
              <Link
                key={type}
                href={`/dashboard/create?type=${type}`}
                className="group rounded-2xl border border-border-light bg-white p-4 shadow-[0_3px_0_0_var(--color-border-light),0_12px_24px_-10px_rgba(0,0,0,0.06)] transition hover:-translate-y-1 hover:border-primary/25 hover:shadow-[0_4px_0_0_var(--color-primary-50),0_16px_28px_-10px_rgba(220,38,38,0.18)]"
              >
                <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)] transition group-hover:scale-110`}>
                  <Icon className={`h-5 w-5 ${color}`} />
                </div>
                <p className="font-semibold text-text-primary">{label}</p>
              </Link>
            );
          })}
          <a
            href="https://zehn.rahnamo.tj/"
            className="group rounded-2xl border border-border-light bg-white p-4 shadow-[0_3px_0_0_var(--color-border-light),0_12px_24px_-10px_rgba(0,0,0,0.06)] transition hover:-translate-y-1 hover:border-primary/25 hover:shadow-[0_4px_0_0_var(--color-primary-50),0_16px_28px_-10px_rgba(220,38,38,0.18)]"
          >
            <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${gameBg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)] transition group-hover:scale-110`}>
              <GameIcon className={`h-5 w-5 ${gameColor}`} />
            </div>
            <p className="font-semibold text-text-primary">{t("landing.feature.igra.title")}</p>
          </a>
        </div>

        {}
        <Link
          href="/dashboard/create?type=all"
          className="group relative mt-3 flex items-center gap-4 overflow-hidden rounded-2xl bg-gradient-to-br from-primary-light via-primary to-primary-dark p-5 text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_16px_32px_-10px_rgba(220,38,38,0.4)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_20px_36px_-10px_rgba(220,38,38,0.45)]"
        >
          <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-white/10 blur-2xl" aria-hidden />
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/15 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)]">
            <Layers className="h-5 w-5" />
          </div>
          <div className="relative flex-1">
            <h3 className="font-semibold">{t("home.allInOne")}</h3>
            <p className="text-sm text-white/80">{t("home.allInOneDesc")}</p>
          </div>
          <ChevronRight className="relative h-5 w-5 shrink-0 text-white/70 transition group-hover:translate-x-0.5" />
        </Link>
      </div>

      {}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {LIBRARY_TYPES.map((type, i) => {
          const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
          const label = t(MATERIAL_TYPE_LABEL_KEY[type]);
          const value = stats ? stats[STAT_KEYS[type]] : null;
          const fillPct = value !== null ? Math.max(6, Math.round((value / maxCount) * 100)) : 0;
          return (
            <Reveal key={type} delay={i * 60}>
              <div className="group rounded-2xl border border-border-light bg-white p-4 shadow-[0_3px_0_0_var(--color-border-light),0_12px_24px_-10px_rgba(0,0,0,0.08)] transition hover:-translate-y-1 hover:shadow-[0_4px_0_0_var(--color-border-light),0_16px_28px_-10px_rgba(220,38,38,0.16)]">
                <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg ${bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)] transition group-hover:scale-110`}>
                  <Icon className={`h-4 w-4 ${color}`} />
                </div>
                <p className="text-2xl font-bold text-text-primary">{value ?? "–"}</p>
                <p className="mb-2 text-xs font-medium text-text-secondary">{label}</p>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
                  <div
                    className={`h-full rounded-full ${STAT_BAR_FILL[type]} transition-all duration-700`}
                    style={{ width: `${fillPct}%` }}
                  />
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>

      {}
      <div>
        <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
          <Clock className="h-3.5 w-3.5" />
          {t("home.recent")}
        </h2>
        {recent.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {recent.map((item) => {
              const config = MATERIAL_TYPE_CONFIG[item.type];
              const Icon = config.icon;
              return (
                <Link
                  key={`${item.type}-${item.id}`}
                  href={item.type === "prezentatsiya" ? `/dashboard/presentations/${item.id}/edit` : `/dashboard/materials/${item.type}/${item.id}`}
                  className="flex items-center gap-3 rounded-2xl border border-border-light bg-white p-3 shadow-[0_2px_0_0_var(--color-border-light)] transition hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-[0_3px_0_0_var(--color-primary-50),0_10px_20px_-8px_rgba(220,38,38,0.15)]"
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${config.bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
                    <Icon className={`h-4 w-4 ${config.color}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-text-primary">{item.title}</p>
                    <p className="truncate text-xs text-text-tertiary">
                      {t(MATERIAL_TYPE_LABEL_KEY[item.type])} • {item.subject}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border-light bg-white/60 p-5 text-center text-sm text-text-tertiary">
            {t("home.recent")}
          </div>
        )}
      </div>

      {}
      {banner?.enabled && (
        <div className="mt-8">
          <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
            <Gift className="h-3.5 w-3.5" />
            {t("home.bonuses")}
          </h2>
          <div className="rounded-2xl border border-border-light bg-white p-5 shadow-[0_3px_0_0_var(--color-border-light),0_12px_24px_-10px_rgba(0,0,0,0.06)]">
            <h3 className="font-semibold text-text-primary">{banner.title}</h3>
            {banner.subtitle && <p className="mt-1 text-sm text-text-secondary">{banner.subtitle}</p>}
            {banner.button_text && (
              <span className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white">
                {banner.button_text}
                <ArrowRight className="h-4 w-4" />
              </span>
            )}
          </div>
        </div>
      )}
      <div className="h-8" />
    </div>
  );
}
