"use client";

import { ShuffleQuestion } from "./types";


export default function FlyingQuestionCard({
  question,
  mode,
  offsetX,
  offsetY,
  centerYOffset,
  compact = false,
  playKey,
}: {
  question: ShuffleQuestion;
  mode: "reveal" | "into" | "outOf" | "settled";
  offsetX: number;
  offsetY: number;
  
  centerYOffset: number;
  
  compact?: boolean;
  
  playKey: string | number;
}) {
  const animation =
    mode === "into"
      ? "mbox-card-into-box 1.15s cubic-bezier(0.55,0,0.85,0.35) forwards"
      : mode === "outOf"
        ? "mbox-card-out-of-box 0.95s cubic-bezier(0.2,0.9,0.35,1.2) forwards"
        : mode === "reveal"
          ? "game-round-in 0.45s ease-out"
          : undefined;

  return (
    <div
      key={`${playKey}-${mode}`}
      className={`pointer-events-none absolute left-1/2 z-40 -translate-x-1/2 -translate-y-1/2 ${
        compact ? "w-[min(240px,60vw)]" : "w-[min(440px,88vw)]"
      }`}
      style={{ top: `calc(50% + ${centerYOffset}px)` }}
      aria-live="polite"
    >
      <div
        className="relative"
        style={{
          ["--fx" as string]: `${offsetX}px`,
          ["--fy" as string]: `${offsetY}px`,
          animation,
        }}
      >
        {}
        <span
          className="pointer-events-none absolute -inset-3 rounded-[28px] bg-gradient-to-br from-amber-300 via-fuchsia-400 to-violet-500 opacity-70 blur-xl"
          style={{ animation: "mbox-glow 1.6s ease-in-out infinite" }}
          aria-hidden
        />

        <div className="relative rounded-3xl border-[3px] border-amber-300/70 bg-white/97 px-5 py-5 text-center shadow-2xl">
          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-fuchsia-600">Савол</p>
          <p className={`mt-2 font-black leading-snug text-[#3b0764] ${compact ? "text-xs" : "text-lg sm:text-xl"}`}>
            {question.question}
          </p>

          {}
          {[
            "-left-2 -top-2",
            "-right-2 -top-2",
            "-bottom-2 -left-2",
            "-bottom-2 -right-2",
          ].map((pos, i) => (
            <span
              key={pos}
              className={`pointer-events-none absolute ${pos} text-base`}
              style={{ animation: `wheel-bulb-twinkle 1.4s ease-in-out ${i * 0.2}s infinite` }}
              aria-hidden
            >
              ✨
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
