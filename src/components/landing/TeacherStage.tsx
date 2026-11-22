"use client";

import Image from "next/image";
import { Sparkles, Check, Star } from "lucide-react";
import { useT } from "@/lib/i18n";

/* Small decorative sparkles scattered around the sticker photo, matching
 * the scattered stars in Hero.tsx — pure decoration, aria-hidden. */
const STAGE_STARS = [
  { top: "2%", left: "0%", size: 20, rotate: -10, opacity: 0.9 },
  { top: "8%", left: "90%", size: 15, rotate: 20, opacity: 0.8 },
  { top: "88%", left: "6%", size: 14, rotate: 12, opacity: 0.7 },
] as const;

/* A "stage" for the hero illustration: a soft static glow behind the
 * sticker-cutout photo, with floating chips and a couple of sparkles. */
export default function TeacherStage() {
  const t = useT();

  return (
    <div className="relative mx-auto w-full max-w-[36rem] py-6">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[25rem] w-[25rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/[0.14] blur-3xl"
        aria-hidden
      />

      {STAGE_STARS.map((s, i) => (
        <Star
          key={i}
          className="pointer-events-none absolute z-20 fill-white text-white"
          style={{
            top: s.top, left: s.left, width: s.size, height: s.size,
            opacity: s.opacity, transform: `rotate(${s.rotate}deg)`,
            animation: `landing-sparkle-twinkle ${4 + i}s ease-in-out infinite`,
            animationDelay: `-${i * 0.6}s`,
          }}
          aria-hidden
        />
      ))}

      <div className="relative z-10 flex items-center justify-center">
        <Image
          src="/hero/team-sticker.png"
          alt=""
          width={699}
          height={526}
          priority
          className="h-auto w-full object-contain drop-shadow-[0_20px_30px_rgba(0,0,0,0.25)]"
        />
      </div>

      <div
        className="absolute left-0 top-0 z-20 flex items-center gap-1.5 rounded-full border border-border-light bg-white px-3 py-1.5 text-xs font-semibold text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(220,38,38,0.25)]"
        style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
      >
        <Sparkles className="h-3.5 w-3.5" />
        {t("landing.hero.chipAssistant")}
      </div>
      <div
        className="absolute bottom-6 right-0 z-20 rounded-2xl border border-border-light bg-white px-4 py-2.5 text-xs font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(0,0,0,0.12)]"
        style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out infinite", animationDelay: "-2s" }}
      >
        {t("landing.hero.chipTypes")}
      </div>
      <div
        className="absolute right-0 top-1/3 z-20 flex items-center gap-1.5 rounded-2xl border border-border-light bg-white px-3 py-2 text-xs font-semibold text-success shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(5,150,105,0.25)]"
        style={{ ["--chip-rot" as string]: "3deg", animation: "landing-float-chip 4.5s ease-in-out infinite", animationDelay: "-1s" }}
      >
        <Check className="h-3.5 w-3.5" />
        {t("landing.hero.chipReady")}
      </div>
    </div>
  );
}
