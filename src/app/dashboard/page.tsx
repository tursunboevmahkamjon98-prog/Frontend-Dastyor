"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Layers, ChevronRight, Clock } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { materialsApi, DashboardStats, SearchResultItem } from "@/lib/api";
import { MATERIAL_TYPE_CONFIG, LIBRARY_TYPES, CREATABLE_TYPES, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";
import Reveal from "@/components/Reveal";

const STAT_KEYS: Record<(typeof LIBRARY_TYPES)[number], keyof DashboardStats> = {
  konspekt: "konspekt_count",
  lektsiya: "lecture_count",
  test: "test_count",
  prezentatsiya: "presentation_count",
  amaliy: "practical_count",
};

function greetingKey(): MessageKey {
  const h = new Date().getHours();
  if (h < 5) return "home.greetNight";
  if (h < 12) return "home.greetMorning";
  if (h < 18) return "home.greetDay";
  return "home.greetEvening";
}

export default function DashboardHome() {
  const t = useT();
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<SearchResultItem[]>([]);

  useEffect(() => {
    materialsApi.stats().then(setStats).catch(() => {});
    materialsApi
      .search("")
      
      
      
      
      .then((items) => setRecent(items.filter((i) => i.type !== "igra").slice(0, 3)))
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6 lg:max-w-5xl lg:px-8">
      <div className="mb-7">
        <h1 className="text-xl font-bold text-text-primary sm:text-2xl">
          {t(greetingKey())}, {user?.full_name?.split(" ")[0]}! 👋
        </h1>
        <p className="mt-0.5 text-sm text-text-secondary">{t("home.prompt")}</p>
      </div>

      {}
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {LIBRARY_TYPES.map((type, i) => {
          const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
          const label = t(MATERIAL_TYPE_LABEL_KEY[type]);
          return (
            <Reveal key={type} delay={i * 60}>
              <div
                className={`rounded-2xl border border-border-light ${bg} p-4 transition hover:-translate-y-0.5 hover:shadow-sm`}
              >
                <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-surface/70 ${color}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <p className="text-2xl font-bold text-text-primary">{stats ? stats[STAT_KEYS[type]] : "–"}</p>
                <p className="text-xs font-medium text-text-secondary">{label}</p>
              </div>
            </Reveal>
          );
        })}
      </div>

      {}
      <Link
        href="/dashboard/create?type=all"
        className="mb-3 flex items-center gap-4 rounded-2xl bg-primary p-5 text-white shadow-md shadow-primary/20 transition hover:-translate-y-0.5 hover:bg-primary-dark"
      >
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/15">
          <Layers className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold">{t("home.allInOne")}</h3>
          <p className="text-sm text-white/80">{t("home.allInOneDesc")}</p>
        </div>
        <ChevronRight className="h-5 w-5 shrink-0 text-white/70" />
      </Link>

      {}
      {recent.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
            <Clock className="h-3.5 w-3.5" />
            {t("home.recent")}
          </h2>
          <div className="space-y-2">
            {recent.map((item) => {
              const config = MATERIAL_TYPE_CONFIG[item.type];
              const Icon = config.icon;
              return (
                <Link
                  key={`${item.type}-${item.id}`}
                  href={`/dashboard/materials/${item.type}/${item.id}`}
                  className="flex items-center gap-3 rounded-2xl border border-border-light bg-surface p-3 transition hover:border-primary/30 hover:shadow-sm"
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${config.bg}`}>
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
        </div>
      )}

      {}
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-text-tertiary">{t("home.quickCreate")}</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {CREATABLE_TYPES.map((type) => {
          const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
          const label = t(MATERIAL_TYPE_LABEL_KEY[type]);
          return (
            <Link
              key={type}
              href={`/dashboard/create?type=${type}`}
              className="rounded-2xl border border-border-light bg-surface p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md hover:shadow-black/[0.04]"
            >
              <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${bg}`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <p className="font-semibold text-text-primary">{label}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
