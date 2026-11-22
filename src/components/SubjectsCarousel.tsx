"use client";

import Image from "next/image";
import { SUBJECTS } from "@/lib/material-types";
import { useT } from "@/lib/i18n";

const BG_VARS = [
  "bg-note-bg",
  "bg-test-bg",
  "bg-pres-bg",
  "bg-lecture-bg",
  "bg-amaliy-bg",
  "bg-igra-bg",
];

/* One illustration per subject, in SUBJECTS order (lib/material-types.ts) —
 * real per-subject artwork from public/images/subjects, not generic icons.
 * The three language subjects share the one "til" (language) illustration;
 * there's no separate art per language. */
const SUBJECT_IMAGES = [
  "matematika", "algebra", "geometriya", "informatika", "fizika", "himiya", "biologiya",
  "geografiya", "til", "til", "til", "adabiyot", "tarix_tj", "tarix_dunyo",
];

/* The curated "good" subjects shown as floating badges around the big
 * count in the hero cluster below -- indices into SUBJECTS/SUBJECT_IMAGES
 * that have real artwork, picked for recognizability, not all 29.
 * Position classes are literal (Tailwind arbitrary-value scan), same
 * reasoning as BG_VARS above. */
const HERO_BADGES: { i: number; pos: string }[] = [
  { i: 0, pos: "left-[1%] top-[4%] -rotate-6 sm:left-[6%]" },
  { i: 3, pos: "right-[1%] top-[6%] rotate-3 sm:right-[6%]" },
  { i: 4, pos: "left-[-2%] top-[42%] -rotate-3 sm:left-[0%]" },
  { i: 5, pos: "right-[-2%] top-[40%] rotate-2 sm:right-[0%]" },
  { i: 6, pos: "left-[6%] bottom-[4%] -rotate-2 sm:left-[12%]" },
  { i: 2, pos: "right-[4%] bottom-[6%] rotate-6 sm:right-[10%]" },
];

export default function SubjectsCarousel() {
  const t = useT();

  return (
    <section className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 sm:pb-24">
      <div className="relative mx-auto mb-10 h-[300px] w-full max-w-3xl sm:h-[400px]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(220,38,38,0.1),transparent_70%)]" />
        {HERO_BADGES.map(({ i, pos }) => (
          <div
            key={i}
            className={`absolute z-20 flex items-center gap-2 rounded-2xl border border-border-light bg-white py-1.5 pl-1.5 pr-3 shadow-[0_2px_0_0_var(--color-border-light),0_14px_24px_-16px_rgba(15,23,42,0.24)] sm:py-2 sm:pl-2 sm:pr-4 ${pos}`}
          >
            <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg sm:h-9 sm:w-9 ${BG_VARS[i % BG_VARS.length]}`}>
              <Image src={`/images/subjects/${SUBJECT_IMAGES[i]}.svg`} alt="" width={20} height={20} className="h-4 w-4 object-contain sm:h-[22px] sm:w-[22px]" />
            </span>
            <span className="text-[11px] font-bold text-text-primary sm:text-sm">{SUBJECTS[i]}</span>
          </div>
        ))}
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-center">
          <span className="text-[30vw] font-black leading-none text-text-primary sm:text-[11rem]">
            {SUBJECTS.length}
          </span>
          <span className="mt-2 text-[11px] font-bold uppercase tracking-[0.2em] text-text-secondary sm:text-sm">
            {t("landing.subjects.count")} <span className="text-primary">{t("landing.subjects.any")}</span>
          </span>
        </div>
      </div>
    </section>
  );
}
