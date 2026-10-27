"use client";

import { Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n";

/* Real output, not a drawing of it.
 *
 * This started as clip art (a stick figure at a whiteboard), then became
 * skeleton bars. Both were a picture *about* the product. These are the
 * actual pages Dastyor generated - the same files the samples gallery
 * further down shows at full size - so the first thing a teacher sees is
 * the thing they are being asked to trust.
 *
 * The konspekt page is cropped to its top half: the part with the heading,
 * the objectives and the key-concepts block is what makes it recognisable
 * as a lesson note, and the white space below it is not worth the height. */

/* WebP copies sized to how they actually render here, generated from the
 * full-size samples with sharp (see the note in scripts/README.md). The
 * originals are ~100 KB each and 834 px wide for a card that paints at ~310
 * CSS px; serving them as-is costs 300 KB of hero on a connection that may
 * well be mobile data. These three total 72 KB. */
const KONSPEKT = "/samples/hero/konspekt.webp";
const TEST = "/samples/hero/test.webp";
const SLIDE = "/samples/hero/slide.webp";

export default function HeroDocuments() {
  const t = useT();

  return (
    <div className="relative mx-auto aspect-[4/3.3] w-full max-w-lg">
      <div
        className="pointer-events-none absolute inset-8 -z-10 rounded-full bg-primary/[0.07] blur-3xl"
        aria-hidden
      />

      {/* Slide, back left */}
      <div className="absolute left-0 top-12 w-[52%] -rotate-[7deg] overflow-hidden rounded-card border border-border-light bg-surface shadow-card-lift">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={SLIDE} alt="" className="block w-full" />
      </div>

      {/* Test, back right */}
      <div className="absolute right-0 top-0 h-[62%] w-[44%] rotate-[7deg] overflow-hidden rounded-card border border-border-light bg-surface shadow-card-lift">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={TEST} alt="" className="block w-full" />
      </div>

      {/* Konspekt, front - the product's main output, so it overlaps both */}
      <div className="absolute bottom-0 left-[10%] h-[76%] w-[60%] overflow-hidden rounded-card border border-border bg-surface shadow-float">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={KONSPEKT} alt="" className="block w-full" fetchPriority="high" />
      </div>

      <span className="absolute bottom-8 right-1 flex items-center gap-1.5 rounded-full border border-border-light bg-surface px-3 py-1.5 text-micro font-semibold text-primary-accent shadow-card">
        <Sparkles className="h-3 w-3" />
        {t("landing.hero.chipReady")}
      </span>
    </div>
  );
}
