"use client";

import { Heart, Star, Flame } from "lucide-react";
import { STARTING_LIVES } from "./types";


export default function ScoreHUD({
  playerName,
  round,
  totalRounds,
  score,
  lives,
  streak,
}: {
  playerName: string;
  round: number; 
  
  totalRounds: number;
  score: number;
  lives: number;
  streak: number;
}) {
  const progress = ((round + 1) / totalRounds) * 100;

  return (
    <>
      {}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-30 flex items-start justify-between gap-2 p-3 sm:p-4">
        {}
        <div className="flex items-center gap-2 rounded-2xl bg-black/35 px-3 py-2 shadow-lg backdrop-blur-md">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-400 to-violet-600 text-xs font-black text-white ring-2 ring-white/40">
            {playerName.trim().charAt(0).toUpperCase() || "?"}
          </span>
          <span className="hidden max-w-[120px] truncate text-xs font-bold text-white sm:block">{playerName}</span>
        </div>

        {}
        <div className="rounded-2xl bg-black/35 px-4 py-2 text-center shadow-lg backdrop-blur-md">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-white/60">Раунд</p>
          <p className="text-sm font-black text-white">
            {round + 1} / {totalRounds}
          </p>
        </div>

        {}
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex items-center gap-1.5 rounded-2xl bg-black/35 px-3 py-2 shadow-lg backdrop-blur-md">
            <Star className="h-4 w-4 shrink-0 fill-amber-300 text-amber-300" />
            <span key={score} className="text-sm font-black text-white" style={{ animation: "mbox-score-bump 0.45s ease-out" }}>
              {score}
            </span>
          </div>
          <div className="flex items-center gap-1 rounded-2xl bg-black/35 px-3 py-1.5 shadow-lg backdrop-blur-md">
            {Array.from({ length: STARTING_LIVES }, (_, i) => (
              <Heart
                key={i}
                className={`h-3.5 w-3.5 transition-all ${i < lives ? "scale-100 fill-red-400 text-red-400" : "scale-90 text-white/25"}`}
              />
            ))}
          </div>
          {streak >= 2 && (
            <div
              className="flex items-center gap-1 rounded-2xl bg-orange-500/80 px-2.5 py-1 shadow-lg backdrop-blur-md"
              style={{ animation: "mascot-pop 0.35s ease-out" }}
            >
              <Flame className="h-3 w-3 text-white" />
              <span className="text-[11px] font-black text-white">{streak}</span>
            </div>
          )}
        </div>
      </div>

      {}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 px-4 pb-3 sm:px-8 sm:pb-4">
        <div className="mx-auto h-2 w-full max-w-lg overflow-hidden rounded-full bg-black/40 backdrop-blur-sm">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amber-300 via-fuchsia-400 to-violet-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </>
  );
}
