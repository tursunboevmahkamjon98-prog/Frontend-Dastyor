"use client";

import { ShuffleQuestion } from "./types";

/** The question card itself — the object the whole game is about. It is the
 * SAME card in all three states, which is the point: the player watches this
 * exact card get shown, fly into a box, and later fly back out of whichever
 * box they opened.
 *
 * `mode` picks which of those it's currently doing:
 *  - "reveal"   — sits big in the centre, being memorised
 *  - "into"     — shrinks and flies into the target box
 *  - "outOf"    — flies back out of the opened box into the centre
 *  - "settled"  — parked in the centre, ready for the answer buttons
 *
 * The flight path is driven by `offsetX`/`offsetY`, the pixel delta from the
 * centre of the stage to the centre of the box involved — computed by the
 * parent from that box's real slot, so the card genuinely aims at the box on
 * screen rather than at a hardcoded guess. */
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
  /** Shifts where "centre" is for this card, in px. Once the answer buttons
   * are on screen the card has to rest higher than the true middle or the
   * two would overlap — and because the flight animations end at
   * translate(0,0), moving the rest point here keeps the landing spot and
   * the parked spot identical instead of making the card jump after it
   * lands. The caller compensates `offsetY` by the same amount so the
   * flight still aims at the real box. */
  centerYOffset: number;
  /** Smaller card, used when three of them fly into the boxes at once —
   * three full-size cards would overlap into an unreadable pile. */
  compact?: boolean;
  /** Changing this remounts the card so a one-shot flight animation
   * replays from the start on every round instead of only the first. */
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
        {/* Magic aura behind the card while it's in flight or on show. */}
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

          {/* Corner sparkles — sells it as a magical object rather than a
              plain modal. */}
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
