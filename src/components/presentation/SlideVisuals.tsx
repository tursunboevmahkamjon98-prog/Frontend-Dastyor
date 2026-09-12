"use client";

import { API_ORIGIN } from "@/lib/api";

export interface VisualBlock {
  type: "table" | "comparison" | "process" | "chart" | "figure";
  data: {
    headers?: string[];
    rows?: string[][];
    criteria?: string[];
    items?: { name: string; values: string[] }[];
    steps?: { title: string; description?: string }[];
    chart_type?: "bar" | "pie" | "line";
    categories?: string[];
    series?: { name: string; values: number[] }[];
    shape?: string;
    values?: string[];
  };
  // A figure_builder drawing (see ai_service.py's _render_slide_figures)
  // stamps these two directly onto the visual, not into `data` — mirrors
  // how a konspekt's `content.figures` entries carry "image"/"caption"
  // alongside "shape"/"values" rather than nested inside them.
  image?: string;
  caption?: string;
}

// n distinguishable shades of one accent color for chart wedges/bars —
// mirrors export_builder.py's _chart_color_shades so the in-app preview's
// palette matches the real PPTX chart's palette.
export function chartShade(accentHex: string, i: number, n: number): string {
  const hex = accentHex.replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  if (n <= 1) return accentHex;
  const t = i / (n - 1);
  const factor = 0.62 + t * 0.7;
  const clamp = (v: number) => Math.min(255, Math.round(v * factor));
  return `rgb(${clamp(r)}, ${clamp(g)}, ${clamp(b)})`;
}

// Renders one slide's "visual" block (table/comparison/process/chart/
// figure) identically wherever a slide is shown — the read-only viewer,
// the fullscreen PresentMode, and the new 3-pane Slide Editor's canvas
// all import this instead of each drawing their own copy.
export default function VisualBlockView({ visual, accent }: { visual: VisualBlock; accent: string }) {
  const { type, data } = visual;

  if (type === "figure") {
    // A figure_builder line drawing (cube, parabola, atom model, circuit
    // — see ai_service.py's _render_slide_figures), same PNG the PPTX/PDF
    // export embeds. No image means the render failed server-side and
    // the "visual" key was dropped entirely, so this only ever sees one
    // that actually exists.
    if (!visual.image) return null;
    return (
      <div className="my-2 flex flex-col items-center rounded-xl border border-border-light bg-surface p-3">
        <img
          src={`${API_ORIGIN}${visual.image}`}
          alt={visual.caption ?? ""}
          className="max-h-[min(45vh,22rem)] w-auto max-w-full object-contain"
        />
        {visual.caption && <p className="mt-1.5 text-center text-xs text-text-tertiary">{visual.caption}</p>}
      </div>
    );
  }

  if (type === "chart") {
    const categories = data.categories ?? [];
    const series = data.series ?? [];
    const values = series[0]?.values ?? [];
    if (!categories.length || !values.length) return null;
    const chartType = data.chart_type ?? "bar";

    if (chartType === "pie") {
      const total = values.reduce((a, b) => a + b, 0) || 1;
      // Cumulative sums computed as their own pass (not a mutable `acc`
      // closed over by .map's callback) — a variable reassigned from
      // inside a render-time .map is exactly the kind of stateful mutation
      // React's compiler/lint rules flag, since a future React optimization
      // is allowed to re-run or memoize that callback independently.
      const cumulative = values.reduce<number[]>((sums, v, i) => {
        sums.push((sums[i - 1] ?? 0) + v);
        return sums;
      }, []);
      const stops = categories.map((_, i) => {
        const start = ((cumulative[i - 1] ?? 0) / total) * 100;
        const end = (cumulative[i] / total) * 100;
        return `${chartShade(accent, i, categories.length)} ${start}% ${end}%`;
      });
      return (
        <div className="my-2 flex flex-col items-center gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div
            className="h-24 w-24 shrink-0 rounded-full sm:h-28 sm:w-28"
            style={{ background: `conic-gradient(${stops.join(", ")})` }}
          />
          <div className="w-full min-w-0 space-y-1 text-xs">
            {categories.map((cat, i) => (
              <div key={i} className="flex items-baseline gap-1.5">
                <span
                  className="mt-[0.15rem] h-2.5 w-2.5 shrink-0 self-center rounded-sm"
                  style={{ backgroundColor: chartShade(accent, i, categories.length) }}
                />
                <span className="min-w-0 break-words text-text-primary">{cat}</span>
                <span className="ml-auto shrink-0 tabular-nums text-text-tertiary">{values[i]}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // "bar" and "line" both render as simple horizontal bars here — this is
    // just the in-app preview (the real PPTX export draws an actual native
    // bar/line chart, see export_builder.py), so a lightweight, dependable
    // representation of the same numbers is enough rather than pulling in
    // a charting library just for this preview.
    const max = Math.max(...values, 1);
    return (
      <div className="my-2 space-y-1.5">
        {categories.map((cat, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-[30%] max-w-[9rem] shrink-0 break-words leading-tight text-text-secondary">
              {cat}
            </span>
            <div className="h-3 min-w-0 flex-1 overflow-hidden rounded bg-surface-muted">
              <div className="h-full rounded" style={{ width: `${((values[i] ?? 0) / max) * 100}%`, backgroundColor: accent }} />
            </div>
            <span className="w-8 shrink-0 text-right tabular-nums text-text-tertiary">{values[i]}</span>
          </div>
        ))}
      </div>
    );
  }

  if (type === "process") {
    const steps = data.steps ?? [];
    if (!steps.length) return null;
    // Conspect notes, matching what the PPTX now draws (see
    // export_builder.py's "process" branch): a numbered heading with its
    // explanation under it, down the slide. The tinted cards with
    // circled numbers that used to be here were dropped on both sides —
    // three real sentences never fitted the three-across strip, so the
    // text spilled out of its boxes.
    return (
      <div className="my-2 space-y-2.5">
        {steps.map((step, i) => (
          <div key={i} className="flex gap-2">
            <span className="w-5 shrink-0 text-sm font-bold" style={{ color: accent }}>
              {i + 1}.
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-text-primary">{step.title}</p>
              {step.description && (
                <p className="mt-0.5 text-xs leading-snug text-text-secondary">{step.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const headers = type === "table" ? data.headers ?? [] : ["", ...(data.criteria ?? [])];
  const rows =
    type === "table" ? data.rows ?? [] : (data.items ?? []).map((it) => [it.name, ...it.values]);
  if (!headers.length || !rows.length) return null;

  return (
    <div className="my-2 overflow-x-auto rounded-lg border border-border-light">
      <table className="w-full min-w-max text-left text-xs">
        <thead>
          <tr style={{ backgroundColor: accent }}>
            {headers.map((h, i) => (
              <th key={i} className="px-2.5 py-1.5 font-semibold text-white">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ backgroundColor: i % 2 === 0 ? `${accent}14` : undefined }}>
              {row.map((cell, j) => (
                <td key={j} className={`px-2.5 py-1.5 text-text-primary ${j === 0 && type === "comparison" ? "font-semibold" : ""}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// The per-slide header treatment for the 5 mockup "header" styles a deck
// template can pick (bar/underline/smallcaps/numbered/serif) — shared so
// the read-only card view and the editor's canvas render an identical
// header for the same template.
export function SlideHeader({
  index,
  title,
  accent,
  header,
}: {
  index: number;
  title: string;
  accent: string;
  header: "bar" | "underline" | "numbered" | "smallcaps" | "serif";
}) {
  if (header === "bar") {
    return (
      <div
        className="px-4 py-3"
        style={{ background: `linear-gradient(100deg, ${accent} 0%, ${accent}cc 100%)` }}
      >
        <p className="break-words text-base font-bold leading-snug text-white">
          {index + 1}. {title}
        </p>
      </div>
    );
  }
  if (header === "underline") {
    return (
      <div className="px-4 pt-4">
        <p className="text-xs font-bold tracking-widest" style={{ color: accent }}>
          {String(index + 1).padStart(2, "0")}
        </p>
        <p className="break-words text-base font-bold uppercase leading-snug text-text-primary">{title}</p>
        <div className="mt-2 h-1 w-10 rounded-full" style={{ backgroundColor: accent }} />
      </div>
    );
  }
  if (header === "smallcaps") {
    return (
      <div className="px-4 pt-4 pb-2.5">
        <p className="text-[11px] font-bold uppercase tracking-widest" style={{ color: accent }}>
          Слайд {String(index + 1).padStart(2, "0")}
        </p>
        <p className="break-words text-base font-bold leading-snug text-text-primary">{title}</p>
        <div className="mt-2 h-px w-full" style={{ backgroundColor: `${accent}33` }} />
      </div>
    );
  }
  // "numbered" (klassik) and "serif" (rasmiy) share the same layout, just
  // differing by the parent's serif font swap above — the number gets its
  // own filled badge so the slide reads as a slide, not a numbered list item.
  return (
    <div className="flex items-start gap-2.5 px-4 pt-4">
      <span
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white"
        style={{ backgroundColor: header === "serif" ? "#334155" : accent }}
      >
        {index + 1}
      </span>
      <p
        className="min-w-0 break-words pt-0.5 text-base font-bold leading-snug"
        style={{ color: header === "serif" ? "#334155" : accent }}
      >
        {title}
      </p>
    </div>
  );
}
