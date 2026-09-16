"use client";

import { OPTION_LETTERS, REAGENT_COLORS } from "./types";
import { labSfx } from "./sounds";


export default function ReagentBottle({
  index,
  label,
  onPick,
  interactive,
  flying,
  dimmed,
  reveal,
  
  flyTo,
}: {
  index: number;
  label: string;
  onPick: () => void;
  interactive: boolean;
  flying: boolean;
  dimmed: boolean;
  reveal: null | "correct" | "wrong";
  flyTo: { x: number; y: number };
}) {
  const c = REAGENT_COLORS[index % REAGENT_COLORS.length];

  return (
    <button
      type="button"
      disabled={!interactive}
      onClick={onPick}
      onMouseEnter={() => interactive && labSfx.hover()}
      className={`group relative flex w-[76px] shrink-0 flex-col items-center outline-none sm:w-[92px] ${
        interactive ? "cursor-pointer" : "cursor-default"
      }`}
      aria-label={`${OPTION_LETTERS[index]}: ${label}`}
      style={{
        opacity: dimmed ? 0.3 : 1,
        filter: dimmed ? "saturate(0.4) brightness(0.6)" : undefined,
        transition: "opacity 0.4s ease, filter 0.4s ease",
      }}
    >
      {}
      <div
        className={`relative transition-transform duration-200 ${
          interactive ? "group-hover:-translate-y-2 group-hover:scale-[1.07] group-active:scale-95" : ""
        }`}
        style={{
          ["--tx" as string]: `${flyTo.x}px`,
          ["--ty" as string]: `${flyTo.y}px`,
          animation: flying
            ? "lab-bottle-pour 1.5s cubic-bezier(0.4,0,0.3,1) forwards"
            : "lab-bottle-idle 3.4s ease-in-out infinite",
        }}
      >
        {}
        <span
          className="pointer-events-none absolute -inset-2 rounded-[26px] blur-lg transition-opacity duration-300"
          style={{
            background: reveal === "correct" ? "#34d399" : reveal === "wrong" ? "#f87171" : c.glow,
            opacity: reveal ? 0.9 : 0.35,
          }}
          aria-hidden
        />

        {}
        <span className="relative block">
          {}
          <span className="mx-auto block h-3 w-5 rounded-t-md bg-gradient-to-b from-amber-600 to-amber-800 shadow-sm" />
          {}
          <span className="mx-auto block h-3.5 w-4 bg-white/25" />
          {}
          <span
            className="relative mx-auto block h-[62px] w-[48px] overflow-hidden rounded-b-[18px] rounded-t-lg border border-white/40 shadow-[inset_0_-8px_14px_rgba(0,0,0,0.35),0_8px_18px_rgba(0,0,0,0.45)] sm:h-[80px] sm:w-[58px]"
            style={{ background: "linear-gradient(115deg, rgba(255,255,255,0.28), rgba(255,255,255,0.06))" }}
          >
            {}
            <span
              className="absolute inset-x-0 bottom-0 h-[62%]"
              style={{ background: `linear-gradient(to bottom, ${c.liquid}, ${c.deep})` }}
            >
              {}
              <span className="absolute inset-x-0 top-0 h-1.5 bg-white/40" />
            </span>
            {}
            {[0, 1, 2, 3].map((b) => (
              <span
                key={b}
                className="absolute bottom-1.5 rounded-full bg-white/70"
                style={{
                  left: `${18 + b * 18}%`,
                  width: 3 + (b % 2),
                  height: 3 + (b % 2),
                  ["--rise" as string]: "-38px",
                  animation: `lab-bubble ${2 + b * 0.4}s ease-in ${b * 0.5}s infinite`,
                }}
                aria-hidden
              />
            ))}
            {}
            <span className="absolute inset-y-2 left-2 w-2 rounded-full bg-white/45 blur-[1px]" />
          </span>

          {}
          {flying && (
            <span
              className="absolute left-1/2 top-full h-16 w-2 origin-top -translate-x-1/2 rounded-full"
              style={{
                background: `linear-gradient(to bottom, ${c.liquid}, transparent)`,
                animation: "lab-stream 1.5s ease-in forwards",
              }}
              aria-hidden
            />
          )}
        </span>

        {}
        <span
          className="absolute -right-1 top-6 flex h-6 w-6 items-center justify-center rounded-lg text-xs font-black text-white shadow-md ring-1 ring-white/40"
          style={{ background: c.deep }}
        >
          {OPTION_LETTERS[index]}
        </span>
      </div>

      {}
      <span
        className={`mt-2 flex h-12 w-full items-center justify-center rounded-xl border px-1.5 py-1 text-center text-[10px] font-bold leading-tight transition sm:h-14 sm:text-[11px] ${
          reveal === "correct"
            ? "border-emerald-300/70 bg-emerald-400/25 text-emerald-50"
            : reveal === "wrong"
              ? "border-red-300/70 bg-red-400/25 text-red-50"
              : "border-white/20 bg-white/10 text-white/90 backdrop-blur-sm group-hover:border-cyan-300/60 group-hover:bg-white/20"
        }`}
      >
        {}
        <span className="line-clamp-3">{label}</span>
      </span>
    </button>
  );
}
