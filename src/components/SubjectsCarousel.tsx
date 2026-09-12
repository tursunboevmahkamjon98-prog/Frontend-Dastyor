"use client";

import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { SUBJECTS } from "@/lib/material-types";

// Cycles through the same pastel category tokens the rest of the site
// already uses (see globals.css) — SUBJECTS has more entries than colours,
// so it just repeats, same as a real palette-based design system would.
const BG_VARS = [
  "bg-note-bg text-note-icon",
  "bg-test-bg text-test-icon",
  "bg-pres-bg text-pres-icon",
  "bg-lecture-bg text-lecture-icon",
  "bg-amaliy-bg text-amaliy-icon",
  "bg-igra-bg text-igra-icon",
];

/** Landing-page "which subjects Dastyor covers" strip — a real, honest
 * list (lib/material-types.ts's SUBJECTS, the same list the create-material
 * wizard offers), not an invented per-subject lesson count. */
export default function SubjectsCarousel() {
  const trackRef = useRef<HTMLDivElement>(null);

  function scroll(dir: 1 | -1) {
    trackRef.current?.scrollBy({ left: dir * 280, behavior: "smooth" });
  }

  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-text-primary sm:text-3xl">
            {SUBJECTS.length} предметов — <span className="text-primary">любая тема</span>
          </h2>
        </div>
        <div className="hidden shrink-0 gap-2 sm:flex">
          <button
            type="button"
            onClick={() => scroll(-1)}
            aria-label="Прокрутить влево"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-surface text-text-primary transition hover:bg-surface-muted"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => scroll(1)}
            aria-label="Прокрутить вправо"
            className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-surface text-text-primary transition hover:bg-surface-muted"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div ref={trackRef} className="flex gap-3 overflow-x-auto pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {SUBJECTS.map((subject, i) => (
          <div
            key={subject}
            className={`flex w-40 shrink-0 flex-col justify-end rounded-2xl border border-border-light p-4 ${BG_VARS[i % BG_VARS.length]}`}
          >
            <p className="text-sm font-semibold leading-snug">{subject}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
