"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  X, BookOpen, Lightbulb, ClipboardCheck, ClipboardList, Presentation,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type Sample = {
  
  id: string;
  label: string;
  icon: LucideIcon;
  
  pages: number;
  
  aspect: string;
  
  span: string;
};











const SAMPLES: Sample[] = [
  { id: "konspekt", label: "Конспект", icon: BookOpen, pages: 6, aspect: "595/842", span: "" },
  { id: "lektsiya", label: "Лекция", icon: Lightbulb, pages: 4, aspect: "595/842", span: "" },
  { id: "test", label: "Тест", icon: ClipboardCheck, pages: 3, aspect: "595/842", span: "" },
  { id: "amaliy", label: "Практическое задание", icon: ClipboardList, pages: 2, aspect: "595/842", span: "" },
  { id: "prezentatsiya", label: "Презентация", icon: Presentation, pages: 11, aspect: "16/9", span: "col-span-2" },
];

export default function SamplesGallery() {
  const samples = SAMPLES;
  const [open, setOpen] = useState<Sample | null>(null);
  
  
  
  
  
  
  
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

  return (
    <>
      {}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        {samples.map((sample) => (
          <figure
            key={sample.id}
            className={`group overflow-hidden rounded-2xl border border-border-light bg-surface shadow-sm transition hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/10 ${sample.span}`}
          >
            <button
              type="button"
              onClick={() => setOpen(sample)}
              className="block w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label={`${sample.label}: посмотреть все страницы (${sample.pages})`}
            >
              <div
                className="relative overflow-hidden bg-surface-muted"
                style={{ aspectRatio: sample.aspect }}
              >
                <img
                  src={`/samples/${sample.id}/1.png`}
                  alt={`Пример: ${sample.label}`}
                  loading="lazy"
                  className="h-full w-full object-cover object-top transition duration-500 group-hover:scale-[1.03]"
                />
                <span className="absolute bottom-2 right-2 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur-sm">
                  {sample.pages} {pagesWord(sample.pages, sample.id)}
                </span>
              </div>
              <figcaption className="flex items-center gap-2 px-3 py-2.5">
                <sample.icon className="h-4 w-4 shrink-0 text-primary" />
                <span className="text-xs font-semibold text-text-primary">{sample.label}</span>
              </figcaption>
            </button>
          </figure>
        ))}
      </div>

      {open && mounted && createPortal(
        <div
          className="fixed inset-0 z-[100] overflow-y-auto overscroll-contain bg-black/75 p-4 backdrop-blur-md sm:p-8"
          onClick={close}
          role="dialog"
          aria-modal="true"
          aria-label={open.label}
        >
          <div className="sticky top-0 z-10 mx-auto mb-4 flex max-w-4xl items-center justify-between gap-3">
            <p className="rounded-full bg-white/95 px-4 py-2 text-sm font-semibold text-text-primary shadow-lg">
              {open.label}
              <span className="ml-2 font-normal text-text-tertiary">
                {open.pages} {pagesWord(open.pages, open.id)}
              </span>
            </p>
            <button
              type="button"
              onClick={close}
              aria-label="Закрыть"
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
                alt={`${open.label}, страница ${i + 1}`}
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


function pagesWord(n: number, id: string) {
  const slide = id === "prezentatsiya";
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return slide ? "слайд" : "страница";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return slide ? "слайда" : "страницы";
  return slide ? "слайдов" : "страниц";
}
