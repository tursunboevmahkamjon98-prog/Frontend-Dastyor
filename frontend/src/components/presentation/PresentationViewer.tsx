"use client";

import { useState } from "react";
import { BarChart3, ChevronLeft, ChevronRight, GitBranch, Image as ImageIcon, RefreshCw, Table2 } from "lucide-react";
import VisualBlockView, { SlideHeader, type VisualBlock } from "./SlideVisuals";
import { KONSPEKT_TEMPLATES } from "@/lib/material-types";
import { getViewerStrings } from "@/lib/content-lang";

export interface Slide {
  title: string;
  bullet_points?: string[];
  speaker_notes?: string;
  visual?: VisualBlock;
}

type SlideKind = "title" | "divider" | "visual" | "text";

/* Which of four real layouts a slide gets is read off what the slide
 * actually contains, not guessed from its position: the first slide is a
 * title slide, a slide with neither bullets nor a visual is a section
 * divider (a pattern every real deck uses between parts), a slide
 * carrying a table/chart/process/figure gets the layout built around
 * that visual, and everything else is plain text. Nothing here invents
 * content meaning ("this slide is the conclusion") that the data does not
 * already say.
 */
function slideKind(slide: Slide, index: number): SlideKind {
  if (index === 0) return "title";
  if (slide.visual) return "visual";
  if (!slide.bullet_points?.length) return "divider";
  return "text";
}

const VISUAL_ICON: Record<VisualBlock["type"], typeof Table2> = {
  table: Table2,
  comparison: Table2,
  process: GitBranch,
  chart: BarChart3,
  figure: ImageIcon,
};

export default function PresentationViewer({
  content,
  accent,
  language,
  onRegenerateSlide,
  regeneratingSlide,
}: {
  content: Record<string, unknown>;
  accent: string;
  language?: string | null;
  onRegenerateSlide: (index: number) => void;
  regeneratingSlide: number | null;
}) {
  const strings = getViewerStrings(language);
  const slides = (content.slides as Slide[] | undefined) ?? [];
  const tmpl = KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0];
  const header = tmpl.mockup.header;
  const serifFont = header === "serif" ? { fontFamily: "Georgia, 'Times New Roman', serif" } : undefined;
  const [active, setActive] = useState(0);

  if (slides.length === 0) return null;
  const i = Math.min(active, slides.length - 1);
  const slide = slides[i];
  const kind = slideKind(slide, i);
  const isRegenerating = regeneratingSlide === i;

  return (
    <div className="grid gap-4 lg:grid-cols-[13rem_minmax(0,1fr)]">
      {/* ---- Navigator ------------------------------------------------ */}
      <ul className="order-2 flex gap-2.5 overflow-x-auto pb-1 lg:order-1 lg:flex-col lg:overflow-visible lg:pb-0">
        {slides.map((s, idx) => {
          const k = slideKind(s, idx);
          const VisualIcon = s.visual ? VISUAL_ICON[s.visual.type] : null;
          const thisActive = idx === i;
          return (
            <li key={idx} className="w-28 shrink-0 lg:w-auto lg:shrink">
              <button
                type="button"
                onClick={() => setActive(idx)}
                aria-current={thisActive ? "true" : undefined}
                className={`block w-full overflow-hidden rounded-control border text-left transition-colors duration-150 ${
                  thisActive ? "border-primary ring-1 ring-primary" : "border-border-light hover:border-border"
                }`}
              >
                <div
                  className="flex aspect-video w-full flex-col justify-between p-2"
                  style={{
                    background:
                      k === "divider"
                        ? `${accent}14`
                        : `linear-gradient(135deg, ${accent}08 0%, #ffffff 60%)`,
                  }}
                >
                  <span className="h-1 w-5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                  <p className="line-clamp-2 text-[0.6rem] font-semibold leading-tight text-text-primary">
                    {s.title}
                  </p>
                </div>
                <div className="flex items-center justify-between border-t border-border-light bg-surface px-1.5 py-1">
                  <span className="text-[0.6rem] tabular-nums text-text-tertiary">{idx + 1}</span>
                  {VisualIcon && <VisualIcon className="h-2.5 w-2.5 text-text-tertiary" strokeWidth={2.2} />}
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {/* ---- Canvas ----------------------------------------------------- */}
      <div className="order-1 min-w-0 lg:order-2">
        <div
          className="relative aspect-video w-full overflow-hidden rounded-card border border-border-light bg-white shadow-card"
          style={serifFont}
        >
          <button
            type="button"
            onClick={() => onRegenerateSlide(i)}
            disabled={regeneratingSlide !== null}
            title={strings.regenerateSlide}
            className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-surface/90 text-text-secondary shadow-card transition-colors duration-150 hover:bg-surface hover:text-text-primary disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isRegenerating ? "animate-spin" : ""}`} />
          </button>

          {kind === "title" && (
            <div className="flex h-full flex-col items-center justify-center gap-3 px-[8%] text-center">
              <span className="h-1 w-14 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
              <h2 className="text-balance text-[clamp(1.1rem,3.4vw,2rem)] font-bold leading-tight text-text-primary">
                {slide.title}
              </h2>
              {(slide.bullet_points?.length ?? 0) > 0 && (
                <p className="max-w-lg text-[clamp(0.75rem,1.4vw,0.95rem)] text-text-secondary">
                  {slide.bullet_points![0]}
                </p>
              )}
            </div>
          )}

          {kind === "divider" && (
            <div
              className="flex h-full flex-col items-center justify-center gap-3 px-[8%] text-center"
              style={{ background: `${accent}10` }}
            >
              <span className="text-[clamp(0.65rem,1.1vw,0.8rem)] font-bold uppercase tracking-widest" style={{ color: accent }}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <h2 className="text-balance text-[clamp(1.05rem,3vw,1.85rem)] font-bold leading-tight text-text-primary">
                {slide.title}
              </h2>
            </div>
          )}

          {kind === "text" && (
            <div className="flex h-full flex-col overflow-y-auto">
              <SlideHeader index={i} title={slide.title} accent={accent} header={header} />
              <div className="flex-1 px-[8%] py-4">
                <ul className="space-y-2.5 text-[clamp(0.8rem,1.5vw,1rem)] text-text-primary">
                  {(slide.bullet_points ?? []).map((b, j) => (
                    <li key={j} className="flex gap-3">
                      <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                      <span className="min-w-0 break-words leading-relaxed">{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {kind === "visual" && (
            <div className="flex h-full flex-col overflow-y-auto">
              <SlideHeader index={i} title={slide.title} accent={accent} header={header} />
              <div
                className={`flex-1 gap-4 px-[6%] py-3 ${
                  (slide.bullet_points?.length ?? 0) > 0 ? "grid sm:grid-cols-[1fr_1.3fr] sm:items-center" : ""
                }`}
              >
                {(slide.bullet_points?.length ?? 0) > 0 && (
                  <ul className="space-y-2 text-[clamp(0.72rem,1.3vw,0.9rem)] text-text-primary">
                    {slide.bullet_points!.map((b, j) => (
                      <li key={j} className="flex gap-2.5">
                        <span className="mt-[0.5em] h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                        <span className="min-w-0 break-words leading-relaxed">{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="min-w-0 text-[0.7rem]">
                  <VisualBlockView visual={slide.visual!} accent={accent} />
                </div>
              </div>
            </div>
          )}
        </div>

        {slide.speaker_notes && (
          <p className="mt-2.5 rounded-control border-l-[3px] bg-surface-muted px-3 py-2 text-micro italic text-text-secondary" style={{ borderLeftColor: accent }}>
            {slide.speaker_notes}
          </p>
        )}

        <div className="mt-3 flex items-center justify-center gap-4">
          <button
            type="button"
            onClick={() => setActive((n) => Math.max(0, n - 1))}
            disabled={i === 0}
            aria-label={strings.prevSlide}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-text-secondary transition-colors duration-150 hover:bg-surface-muted disabled:opacity-30"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="min-w-[4ch] text-center text-meta tabular-nums text-text-tertiary">
            {i + 1} / {slides.length}
          </span>
          <button
            type="button"
            onClick={() => setActive((n) => Math.min(slides.length - 1, n + 1))}
            disabled={i === slides.length - 1}
            aria-label={strings.nextSlide}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-text-secondary transition-colors duration-150 hover:bg-surface-muted disabled:opacity-30"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
