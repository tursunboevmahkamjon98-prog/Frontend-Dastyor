"use client";

import { Play } from "lucide-react";
import { BOX_THEME } from "./MagicBox";


export default function MagicShuffleCard({ onPlay }: { onPlay: () => void }) {
  return (
    <button
      type="button"
      onClick={onPlay}
      className="group w-full max-w-sm overflow-hidden rounded-3xl border border-border bg-surface text-left shadow-lg transition hover:-translate-y-1 hover:shadow-2xl active:translate-y-0"
    >
      {}
      <div className="relative h-40 w-full overflow-hidden bg-[#1b0f3a]">
        {}
        <img
          src="/game-backgrounds/classroom.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#2e1065]/50 via-[#4c1d95]/40 to-[#1b0f3a]/80" />

        {}
        <span className="absolute left-3 top-3 text-lg font-black text-amber-200/80" style={{ animation: "mbox-float 3s ease-in-out infinite" }}>
          ?
        </span>
        <span className="absolute right-4 top-5 text-sm font-black text-fuchsia-200/70" style={{ animation: "mbox-float 3.4s ease-in-out 0.6s infinite" }}>
          ?
        </span>
        <span className="absolute right-10 top-2 text-amber-200/80" style={{ animation: "wheel-bulb-twinkle 2s ease-in-out infinite" }}>
          ✦
        </span>

        {}
        {}
        <img
          src="/game-backgrounds/jester.png"
          alt=""
          className="absolute bottom-6 left-1/2 h-24 w-auto -translate-x-1/2 drop-shadow-2xl"
          style={{ animation: "mascot-bob 2.8s ease-in-out infinite" }}
        />

        {}
        <div className="absolute bottom-2 left-1/2 flex -translate-x-1/2 items-end gap-3">
          {[0, 1, 2].map((i) => (
            <span key={i} className="relative" style={{ animation: `mbox-float 3s ease-in-out ${i * 0.35}s infinite` }}>
              <span className="absolute inset-0 rounded-lg blur-md" style={{ background: BOX_THEME.glow, opacity: 0.6 }} aria-hidden />
              <span
                className="relative flex h-8 w-8 items-center justify-center rounded-lg text-sm font-black text-white shadow-md"
                style={{ background: BOX_THEME.body, border: `1.5px solid ${BOX_THEME.bodyShade}` }}
              >
                ?
              </span>
            </span>
          ))}
        </div>
      </div>

      {}
      <div className="p-4">
        <span className="inline-flex rounded-full bg-igra-bg px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-igra-icon">
          Маориф
        </span>
        <h3 className="mt-2 text-base font-extrabold text-text-primary">Қуттиҳои сеҳрнок</h3>
        <p className="mt-1 text-xs leading-relaxed text-text-secondary">
          Се савол — се қуттӣ. Онҳоро бодиққат назорат кунед ва яктояшро интихоб кунед!
        </p>
        <span className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 py-2.5 text-sm font-black text-white shadow-md transition group-hover:from-amber-300 group-hover:to-orange-400">
          <Play className="h-4 w-4 fill-white" />
          Бозӣ кардан
        </span>
      </div>
    </button>
  );
}
