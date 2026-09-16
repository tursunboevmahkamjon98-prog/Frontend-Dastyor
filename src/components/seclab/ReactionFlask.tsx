"use client";

import { ReactionConfig } from "./types";


export default function ReactionFlask({
  state,
  config,
  
  tint,
}: {
  state: "idle" | "filling" | "success" | "fail" | "finale";
  config: ReactionConfig;
  tint: string;
}) {
  const reacting = state === "success" || state === "finale";
  const animation =
    state === "success" || state === "finale"
      ? "lab-react-success 1.4s ease-out"
      : state === "fail"
        ? "lab-react-fail 0.7s ease-in-out"
        : undefined;

  const glowColor = state === "fail" ? "#f87171" : state === "idle" ? "#38bdf8" : tint;
  const glowOpacity = state === "idle" ? 0.3 : reacting ? config.intensity : 0.45;

  return (
    <div className="relative flex flex-col items-center" style={{ animation }}>
      {}
      <span
        className="pointer-events-none absolute -inset-6 rounded-full blur-2xl transition-all duration-500"
        style={{ background: glowColor, opacity: glowOpacity }}
        aria-hidden
      />

      {}
      {reacting &&
        Array.from({ length: config.sparks }, (_, i) => {
          const angle = (i / config.sparks) * Math.PI * 2;
          const dist = 60 + (i % 4) * 22;
          return (
            <span
              key={i}
              className="pointer-events-none absolute left-1/2 top-1/3 h-1.5 w-1.5 rounded-full"
              style={{
                background: i % 3 === 0 ? "#fde68a" : tint,
                ["--sx" as string]: `${Math.cos(angle) * dist}px`,
                ["--sy" as string]: `${Math.sin(angle) * dist}px`,
                animation: `lab-spark ${0.8 + (i % 3) * 0.25}s ease-out ${i * 0.03}s forwards`,
              }}
              aria-hidden
            />
          );
        })}

      {}
      {reacting && (
        <span
          className="pointer-events-none absolute -top-8 h-16 w-16 rounded-full blur-xl"
          style={{ background: tint, opacity: 0.5, animation: "lab-smoke 2.4s ease-out infinite" }}
          aria-hidden
        />
      )}

      {}
      <span className="relative block">
        {}
        <span className="mx-auto block h-5 w-5 rounded-t-md border-x border-t border-white/40 bg-white/15 sm:h-6 sm:w-6" />
        {}
        <span
          className="relative block h-[92px] w-[104px] overflow-hidden border border-white/35 shadow-[inset_0_-10px_20px_rgba(0,0,0,0.35),0_10px_26px_rgba(0,0,0,0.5)] sm:h-[116px] sm:w-[128px]"
          style={{
            clipPath: "polygon(38% 0, 62% 0, 100% 100%, 0% 100%)",
            background: "linear-gradient(115deg, rgba(255,255,255,0.26), rgba(255,255,255,0.05))",
            borderRadius: "0 0 22px 22px",
          }}
        >
          {}
          <span
            className="absolute inset-x-0 bottom-0 transition-[height] duration-700 ease-out"
            style={{
              height: state === "idle" ? "26%" : "62%",
              background: `linear-gradient(to bottom, ${tint}, rgba(0,0,0,0.35))`,
              animation: state === "filling" ? "lab-fill 1.2s ease-out forwards" : undefined,
            }}
          >
            <span className="absolute inset-x-0 top-0 h-2 bg-white/45" />
          </span>

          {}
          {Array.from({ length: reacting ? config.bubbles : 4 }, (_, i) => (
            <span
              key={i}
              className="absolute bottom-2 rounded-full bg-white/75"
              style={{
                left: `${12 + ((i * 13) % 74)}%`,
                width: 3 + (i % 3),
                height: 3 + (i % 3),
                ["--rise" as string]: `${-50 - (i % 4) * 12}px`,
                animation: `lab-bubble ${1.1 + (i % 5) * 0.3}s ease-in ${i * 0.14}s infinite`,
              }}
              aria-hidden
            />
          ))}

          {}
          <span className="absolute bottom-3 left-5 h-12 w-2.5 rounded-full bg-white/40 blur-[1px] sm:left-6 sm:h-14" />
        </span>
      </span>

      {}
      <span className="pointer-events-none mt-0.5 h-2 w-20 rounded-[50%] bg-black/55 blur-[5px] sm:h-2.5 sm:w-24" aria-hidden />
    </div>
  );
}
