"use client";

import Link from "next/link";
import Image from "next/image";
import { ArrowRight, BookOpenText, RotateCw } from "lucide-react";
import { MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { CREATE_HREF } from "@/lib/dashboard-nav";
import type { SearchResultItem } from "@/lib/api";
import { useT } from "@/lib/i18n";

export type LoadState = "loading" | "error" | "ready";

const MATERIAL_ART: Record<string, string> = {
  konspekt: "/soft3d/book.webp",
  lektsiya: "/soft3d/notebook.webp",
  test: "/soft3d/quiz.webp",
  prezentatsiya: "/soft3d/presentation.webp",
  amaliy: "/soft3d/notebook.webp",
  igra: "/soft3d/quiz.webp",
};

export default function RecentList({
  state,
  items,
  onRetry,
}: {
  state: LoadState;
  items: SearchResultItem[];
  onRetry: () => void;
}) {
  const t = useT();

  return (
    <section aria-labelledby="recent-title">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-micro font-semibold uppercase tracking-[0.14em] text-primary-accent">
            {t("nav.materials")}
          </p>
          <h2 id="recent-title" className="text-heading font-semibold text-text-primary">
            {t("home.recent")}
          </h2>
        </div>
        {state === "ready" && items.length > 0 && (
          <Link href="/dashboard/materials" className="inline-flex items-center gap-2 text-meta font-semibold text-primary-accent hover:underline">
            {t("home.viewAll")}
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>

      {state === "loading" && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true">
          {[0, 1, 2].map((index) => <div key={index} className="h-28 animate-pulse rounded-2xl border border-border-light bg-surface-muted/60" />)}
        </div>
      )}

      {state === "error" && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-surface px-6 py-7">
          <p className="text-body text-text-secondary">{t("home.loadFailed")}</p>
          <button type="button" onClick={onRetry} className="inline-flex items-center gap-2 rounded-control border border-border px-4 py-2 text-meta font-semibold text-text-primary hover:bg-surface-muted">
            <RotateCw className="h-4 w-4" />
            {t("home.retry")}
          </button>
        </div>
      )}

      {state === "ready" && items.length === 0 && (
        <div className="grid overflow-hidden rounded-[1.5rem] border border-border-light bg-surface shadow-card sm:grid-cols-[minmax(0,1fr)_12rem]">
          <div className="flex flex-col items-start justify-center px-6 py-9 sm:px-9 sm:py-12">
            <span className="mb-5 flex h-11 w-11 items-center justify-center rounded-control bg-primary-50 text-primary-accent">
              <BookOpenText className="h-5 w-5" />
            </span>
            <h3 className="text-subheading font-semibold text-text-primary">{t("home.emptyTitle")}</h3>
            <p className="mt-2 max-w-md text-body text-text-secondary">{t("home.emptyBody")}</p>
            <Link href={CREATE_HREF} className="mt-6 inline-flex items-center gap-2 text-meta font-semibold text-primary-accent hover:underline">
              {t("nav.create")}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="hidden items-end justify-center bg-[linear-gradient(145deg,var(--color-primary-50),var(--color-note-bg))] pt-5 sm:flex">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/mascot/knowledge.webp" alt="" aria-hidden width={512} height={512} draggable={false} className="h-44 w-auto object-contain" />
          </div>
        </div>
      )}

      {state === "ready" && items.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => {
            const config = MATERIAL_TYPE_CONFIG[item.type];
            const Icon = config.icon;
            return (
              <li key={item.type + "-" + item.id}>
                <Link href={"/dashboard/materials/" + item.type + "/" + item.id}
                  className={`group flex min-h-[112px] items-center gap-4 rounded-2xl border border-border-light ${config.bg}/35 px-4 py-4 shadow-card transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-card-lift sm:px-5`}>
                  <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl shadow-[0_5px_12px_rgba(50,35,30,0.07)] ${config.bg} ${config.color}`}>
                    <Icon className="h-5 w-5" strokeWidth={1.8} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="mb-1 block text-micro font-medium text-text-tertiary">{t(MATERIAL_TYPE_LABEL_KEY[item.type])}</span>
                    <span className="block truncate text-meta font-semibold text-text-primary">{item.title}</span>
                    <span className="mt-1 block truncate text-micro text-text-secondary">{item.subject} · {item.grade}</span>
                  </span>
                  <Image src={MATERIAL_ART[item.type]} alt="" aria-hidden="true" width={96} height={96} sizes="52px" className="h-12 w-12 shrink-0 object-contain drop-shadow-[0_6px_8px_rgba(64,44,43,0.12)] sm:h-14 sm:w-14" />
                  <ArrowRight className="h-4 w-4 shrink-0 text-text-tertiary transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-primary-accent" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
