"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  X, BookOpen, Lightbulb, ClipboardCheck, ClipboardList, Presentation,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type Sample = {
  /** Folder under /public/samples holding 1.png … {pages}.png. */
  id: string;
  label: string;
  icon: LucideIcon;
  /** Every page of this material, so the viewer can show the whole thing. */
  pages: number;
  /** CSS aspect-ratio for one page: A4 portrait for documents, 16:9 for the deck. */
  aspect: string;
  /** Grid width of the thumbnail — the deck is wide and takes two columns. */
  span: string;
};

/** The landing page's "how it looks" gallery.
 *
 * A thumbnail on its own only ever proves one page exists, and the first
 * question a teacher has is how long the thing actually is and what is on
 * the rest of it. Clicking opens every page of that material, in order, in
 * a scrollable overlay.
 *
 * Pages are plain <img> under /public/samples/{id}/{n}.png, rendered from
 * the product's own PDF export (see the #samples comment in app/page.tsx).
 * They are only referenced once a sample is opened, so the 2.9 MB of page
 * images across all five materials never touches a first page load —
 * loading="lazy" then keeps even the opened material to what is on screen.
 */
// Lives here rather than in the page because page.tsx is a Server
// Component and these entries carry lucide icons — functions, which React
// refuses to serialise across the server/client boundary ("Functions
// cannot be passed directly to Client Components"). Keeping the list next
// to the only thing that renders it avoids the boundary entirely.
//
// `pages` must match the file count in /public/samples/{id}/ — the viewer
// asks for 1.png … {pages}.png and a wrong number shows a broken image or
// hides a real page.
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
  // The overlay is portalled to <body>, and that is not a style choice.
  // This gallery sits inside <Reveal>, whose landing-reveal animation
  // applies a transform with fill-mode "both" — so the transform is still
  // there after the animation ends. A transformed ancestor becomes the
  // containing block for position:fixed descendants, which pinned the
  // overlay to the section instead of the viewport: dark bars either side
  // of the page, the header still showing above it.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const close = useCallback(() => setOpen(null), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    // The overlay scrolls on its own; letting the page behind scroll too
    // means closing it drops the reader somewhere else entirely.
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open, close]);

  return (
    <>
      {/* Six columns so four portrait pages sit beside a deck that takes
          two — 4 + 2 fills the row exactly. */}
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

          {/* Stops a click that lands on a page from closing the overlay,
              while a click on the backdrop around it still does. */}
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

/** "9 слайдов" for the deck, "6 страниц" for everything else. */
function pagesWord(n: number, id: string) {
  const slide = id === "prezentatsiya";
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return slide ? "слайд" : "страница";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return slide ? "слайда" : "страницы";
  return slide ? "слайдов" : "страниц";
}
