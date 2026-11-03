"use client";

import Image from "next/image";
import { Sparkles, Check } from "lucide-react";
import { useT } from "@/lib/i18n";

/* A "stage" for the hero illustration: a soft static glow behind the
 * still photo, with only the surrounding chips gently floating. */
export default function TeacherStage() {
  const t = useT();

  return (
    <div className="relative mx-auto h-[29rem] w-full max-w-[34rem]">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[25rem] w-[25rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/[0.16] blur-3xl"
        aria-hidden
      />
      <div className="pointer-events-none absolute left-1/2 top-[58%] h-16 w-[62%] -translate-x-1/2 rounded-[50%] bg-primary/15 blur-2xl" aria-hidden />

      <div className="relative z-10 flex h-full items-center justify-center">
        <Image
          src="/hero/teacher.png"
          alt=""
          width={740}
          height={740}
          priority
          className="h-[26rem] w-auto object-contain drop-shadow-[0_20px_26px_rgba(124,58,237,0.2)]"
        />
      </div>

      <div
        className="absolute left-0 top-10 z-20 flex items-center gap-1.5 rounded-full border border-border-light bg-white px-3 py-1.5 text-xs font-semibold text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(220,38,38,0.25)]"
        style={{ ["--chip-rot" as string]: "-3deg", animation: "landing-float-chip 5s ease-in-out infinite" }}
      >
        <Sparkles className="h-3.5 w-3.5" />
        {t("landing.hero.chipAssistant")}
      </div>
      <div
        className="absolute bottom-16 right-0 z-20 rounded-2xl border border-border-light bg-white px-4 py-2.5 text-xs font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(0,0,0,0.12)]"
        style={{ ["--chip-rot" as string]: "2deg", animation: "landing-float-chip 5.5s ease-in-out infinite", animationDelay: "-2s" }}
      >
        {t("landing.hero.chipTypes")}
      </div>
      <div
        className="absolute right-2 top-[38%] z-20 flex items-center gap-1.5 rounded-2xl border border-border-light bg-white px-3 py-2 text-xs font-semibold text-success shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-6px_rgba(5,150,105,0.25)]"
        style={{ ["--chip-rot" as string]: "3deg", animation: "landing-float-chip 4.5s ease-in-out infinite", animationDelay: "-1s" }}
      >
        <Check className="h-3.5 w-3.5" />
        {t("landing.hero.chipReady")}
      </div>
    </div>
  );
}
