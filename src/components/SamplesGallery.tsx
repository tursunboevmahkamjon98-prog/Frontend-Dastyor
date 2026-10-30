"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  X, BookOpen, Lightbulb, ClipboardCheck, ClipboardList, Presentation,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";
import { featureDescKey } from "./landing/constants";

export type Sample = {
  
  id: string;
  labelKey: MessageKey;
  icon: LucideIcon;
  
  pages: number;
  
  aspect: string;
  
};









const SAMPLES: Sample[] = [
  { id: "konspekt", labelKey: "type.konspekt", icon: BookOpen, pages: 6, aspect: "595/842" },
  { id: "lektsiya", labelKey: "type.lektsiya", icon: Lightbulb, pages: 4, aspect: "595/842" },
  { id: "test", labelKey: "type.test", icon: ClipboardCheck, pages: 3, aspect: "595/842" },
  { id: "amaliy", labelKey: "type.amaliy", icon: ClipboardList, pages: 2, aspect: "595/842" },
  { id: "prezentatsiya", labelKey: "type.prezentatsiya", icon: Presentation, pages: 11, aspect: "16/9" },
];

export default function SamplesGallery() {
  const { locale, t } = useLocale();
  const samples = SAMPLES;
  const [open, setOpen] = useState<Sample | null>(null);
  const [selected, setSelected] = useState<Sample>(SAMPLES[0]);
  const SelectedIcon = selected.icon;
  
  
  
  
  
  
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const close = useCallback(() => setOpen(null), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    
    
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, close]);

  
  
  const unit = (n: number, id: string) =>
    locale === "ru"
      ? pagesWordRu(n, id)
      : t(id === "prezentatsiya" ? "landing.samples.slides" : "landing.samples.pages");

  return (
    <>
      {}
      <div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)] lg:gap-6">
        <div className="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-2.5 lg:overflow-visible lg:pb-0">
          {samples.map((sample, index) => {
            const Icon = sample.icon;
            const active = selected.id === sample.id;
            return (
              <button
                key={sample.id}
                type="button"
                onClick={() => setSelected(sample)}
                aria-pressed={active}
                className={`group flex min-w-[190px] flex-1 items-center gap-3 rounded-2xl border p-3.5 text-left transition duration-200 lg:min-w-0 ${active
                  ? "border-primary/25 bg-white shadow-[0_3px_0_0_var(--color-primary-50),0_14px_28px_-14px_rgba(220,38,38,0.25)]"
                  : "border-transparent bg-white/55 hover:border-border-light hover:bg-white"
                }`}
              >
                <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl transition ${active ? "bg-primary text-white shadow-[0_3px_0_0_var(--color-primary-dark)]" : "bg-surface-muted text-text-tertiary group-hover:bg-primary-50 group-hover:text-primary"}`}>
                  <Icon className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-text-primary">{t(sample.labelKey)}</span>
                  <span className="mt-0.5 block text-xs text-text-tertiary">{sample.pages} {unit(sample.pages, sample.id)}</span>
                </span>
                <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold ${active ? "bg-primary-50 text-primary" : "text-text-tertiary"}`}>
                  {String(index + 1).padStart(2, "0")}
                </span>
              </button>
            );
          })}
        </div>

        <div className="relative isolate overflow-hidden rounded-[1.75rem] border border-border-light bg-gradient-to-br from-white via-white to-primary-50/70 p-3 shadow-[0_3px_0_0_var(--color-border-light),0_24px_48px_-30px_rgba(127,29,29,0.35)] sm:p-5">
          <div className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-primary/10 blur-3xl" aria-hidden />
          <div className="pointer-events-none absolute -bottom-20 left-8 h-56 w-56 rounded-full bg-note-icon/10 blur-3xl" aria-hidden />
          <div className="relative flex min-h-[25rem] items-center justify-center overflow-hidden rounded-[1.25rem] border border-white/80 bg-[radial-gradient(ellipse_at_50%_45%,rgba(255,255,255,0.95),rgba(255,245,244,0.7)_72%)] px-4 py-12 sm:min-h-[31rem] sm:px-8 sm:py-10">
            <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:radial-gradient(var(--color-primary)_0.6px,transparent_0.6px)] [background-size:20px_20px]" aria-hidden />
            <div className="absolute left-4 top-4 z-10 inline-flex items-center gap-2 rounded-full border border-white bg-white/90 px-3 py-1.5 text-xs font-semibold text-text-secondary shadow-sm backdrop-blur sm:left-5 sm:top-5">
              <SelectedIcon className="h-3.5 w-3.5 text-primary" />
              {t(selected.labelKey)}
            </div>
            <span className="absolute right-4 top-4 z-10 rounded-full border border-white bg-white/90 px-3 py-1.5 text-xs font-semibold text-text-tertiary shadow-sm backdrop-blur sm:right-5 sm:top-5">
              {selected.pages} {unit(selected.pages, selected.id)}
            </span>
            <img
              key={selected.id}
              src={`/samples/${selected.id}/1.png`}
              alt={`${t("landing.samples.exampleAlt")}: ${t(selected.labelKey)}`}
              loading="lazy"
              className={`relative z-[1] h-auto max-h-[min(66vh,34rem)] object-contain drop-shadow-[0_24px_28px_rgba(41,19,21,0.2)] transition duration-300 ${selected.aspect === "16/9" ? "w-full max-w-5xl rounded-xl" : "w-auto max-w-[78%] rounded-sm sm:max-w-[58%]"}`}
              style={{ aspectRatio: selected.aspect }}
            />
            <div className="absolute bottom-4 left-4 z-10 text-[10px] font-semibold tracking-[0.18em] text-primary/45 sm:bottom-5 sm:left-5">DASTYOR · {String(samples.indexOf(selected) + 1).padStart(2, "0")}</div>
          </div>
          <div className="flex flex-col gap-3 px-2 pb-1 pt-4 sm:flex-row sm:items-center sm:justify-between sm:px-1 sm:pt-5">
            <div>
              <h3 className="text-base font-bold text-text-primary sm:text-lg">{t(selected.labelKey)}</h3>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-text-secondary">{t(featureDescKey(selected.id))}</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(selected)}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-border-light bg-white px-4 py-2.5 text-sm font-semibold text-text-primary shadow-[0_2px_0_0_var(--color-border-light)] transition hover:-translate-y-0.5 hover:border-primary/20 hover:text-primary"
            >
              {t("landing.samples.viewAll")}
              <span aria-hidden="true">↗</span>
            </button>
          </div>
        </div>
      </div>

      {open && mounted && createPortal(
        <div
          className="fixed inset-0 z-[100] overflow-y-auto overscroll-contain bg-black/75 p-4 backdrop-blur-md sm:p-8"
          onClick={close}
          role="dialog"
          aria-modal="true"
          aria-label={t(open.labelKey)}
        >
          <div className="sticky top-0 z-10 mx-auto mb-4 flex max-w-4xl items-center justify-between gap-3">
            <p className="rounded-full bg-white/95 px-4 py-2 text-sm font-semibold text-text-primary shadow-lg">
              {t(open.labelKey)}
              <span className="ml-2 font-normal text-text-tertiary">
                {open.pages} {unit(open.pages, open.id)}
              </span>
            </p>
            <button
              type="button"
              onClick={close}
              aria-label={t("landing.samples.close")}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/95 text-text-secondary shadow-lg transition hover:text-text-primary"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {}
          <div
            className="mx-auto flex max-w-4xl flex-col gap-4 pb-4"
            onClick={(e) => e.stopPropagation()}
          >
            {Array.from({ length: open.pages }, (_, i) => (
              <img
                key={i}
                src={`/samples/${open.id}/${i + 1}.png`}
                alt={`${t(open.labelKey)}, ${t("landing.samples.pageAlt")} ${i + 1}`}
                loading="lazy"
                className="w-full rounded-xl bg-white shadow-2xl"
                style={{ aspectRatio: open.aspect }}
              />
            ))}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}


function pagesWordRu(n: number, id: string) {
  const slide = id === "prezentatsiya";
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return slide ? "слайд" : "страница";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return slide ? "слайда" : "страницы";
  return slide ? "слайдов" : "страниц";
}
