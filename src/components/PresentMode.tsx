"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { KONSPEKT_TEMPLATES } from "@/lib/material-types";
import VisualBlockView, { VisualBlock } from "@/components/presentation/SlideVisuals";

export interface PresentSlide {
  title: string;
  bullet_points?: string[];
  speaker_notes?: string;
  visual?: VisualBlock;
}





























export default function PresentMode({
  slides,
  accent,
  template,
  initialIndex = 0,
  onClose,
}: {
  slides: PresentSlide[];
  accent: string;
  template: (typeof KONSPEKT_TEMPLATES)[number];
  initialIndex?: number;
  onClose: () => void;
}) {
  const [i, setI] = useState(() => Math.min(Math.max(initialIndex, 0), Math.max(slides.length - 1, 0)));
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const serifFont = template.mockup.header === "serif" ? { fontFamily: "Georgia, 'Times New Roman', serif" } : undefined;

  const last = slides.length - 1;
  const next = () => setI((n) => Math.min(n + 1, last));
  const prev = () => setI((n) => Math.max(n - 1, 0));

  useEffect(() => {
    containerRef.current?.requestFullscreen?.().catch(() => {});
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
        e.preventDefault();
        setI((n) => Math.min(n + 1, slides.length - 1));
      } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
        e.preventDefault();
        setI((n) => Math.max(n - 1, 0));
      } else if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
    
  }, []);

  
  
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [i]);

  const s = slides[i];
  if (!s) return null;

  
  
  
  
  function onTouchStart(e: React.TouchEvent) {
    const t = e.touches[0];
    touchStart.current = { x: t.clientX, y: t.clientY };
  }
  function onTouchEnd(e: React.TouchEvent) {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    if (dx < 0) next();
    else prev();
  }

  return (
    <div
      ref={containerRef}
      className="present-root fixed inset-0 z-50 flex flex-col overflow-hidden bg-white"
      style={serifFont}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <button
        onClick={onClose}
        aria-label="Закрыть"
        className="present-close absolute z-20 flex h-11 w-11 items-center justify-center rounded-full bg-black/5 text-gray-500 hover:bg-black/10 hover:text-gray-800"
      >
        <X className="h-5 w-5" />
      </button>

      {}
      <div
        ref={scrollRef}
        className="present-body min-h-0 flex-1 overflow-y-auto overscroll-contain"
      >
        <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col items-center justify-center text-center">
          <p
            className="mb-[2vh] text-[clamp(0.65rem,1.4vw,0.9rem)] font-bold uppercase tracking-widest"
            style={{ color: accent }}
          >
            {i + 1} / {slides.length}
          </p>

          {}
          <h2 className="mb-[3vh] w-full text-balance break-words text-[clamp(1.35rem,4.2vw,3.25rem)] font-extrabold leading-tight text-gray-900">
            {s.title}
          </h2>

          {(s.bullet_points?.length ?? 0) > 0 && (
            <ul className="mx-auto mb-[3vh] w-full max-w-3xl space-y-[1.6vh] text-left text-[clamp(0.9rem,2.1vw,1.6rem)] leading-snug text-gray-800">
              {(s.bullet_points ?? []).map((b, j) => (
                <li key={j} className="flex gap-3">
                  <span className="mt-[0.35em] h-[0.4em] w-[0.4em] shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                  <span className="min-w-0 break-words">{b}</span>
                </li>
              ))}
            </ul>
          )}

          {s.visual && (
            <div className="mx-auto w-full max-w-3xl text-left">
              <VisualBlockView visual={s.visual} accent={accent} />
            </div>
          )}
        </div>
      </div>

      {}
      <div className="present-nav flex shrink-0 items-center justify-center gap-4">
        <button
          onClick={prev}
          disabled={i === 0}
          aria-label="Предыдущий слайд"
          className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 text-gray-600 transition hover:bg-gray-50 disabled:opacity-30"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <span className="min-w-[4ch] text-center text-sm tabular-nums text-gray-400">
          {i + 1}/{slides.length}
        </span>
        <button
          onClick={next}
          disabled={i === last}
          aria-label="Следующий слайд"
          className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 text-gray-600 transition hover:bg-gray-50 disabled:opacity-30"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
