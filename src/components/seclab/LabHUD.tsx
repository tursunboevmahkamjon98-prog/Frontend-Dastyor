"use client";

import { Heart, Star } from "lucide-react";
import { STARTING_LIVES, STATIONS, stationForRound } from "./types";
import type { ScorePop } from "./useLabGame";


function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`pointer-events-auto flex items-center gap-2 rounded-2xl border border-white/15 bg-white/10 px-3 py-1.5 shadow-lg backdrop-blur-md transition hover:border-white/30 hover:bg-white/15 ${className}`}
    >
      {children}
    </div>
  );
}


export default function LabHUD({
  playerName,
  round,
  totalRounds,
  score,
  lives,
  scorePops,
}: {
  playerName: string;
  round: number; 
  totalRounds: number;
  score: number;
  lives: number;
  scorePops: ScorePop[];
}) {
  const currentStation = stationForRound(round, totalRounds);
  const progress = ((round + 1) / totalRounds) * 100;

  return (
    <>
      {}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-40 flex items-start justify-between gap-2 p-3 sm:p-4">
        <Chip>
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 text-[11px] font-black text-white ring-2 ring-white/30">
            {playerName.trim().charAt(0).toUpperCase() || "?"}
          </span>
          <span className="hidden max-w-[110px] truncate text-xs font-bold text-white sm:block">{playerName}</span>
        </Chip>

        <Chip className="flex-col !gap-0 px-4">
          <span className="text-[9px] font-bold uppercase tracking-widest text-cyan-200/70">Раунд</span>
          <span className="text-sm font-black text-white">
            {round + 1} / {totalRounds}
          </span>
        </Chip>

        <div className="flex flex-col items-end gap-1.5">
          {}
          <div className="relative">
            <Chip>
              <Star className="h-4 w-4 shrink-0 fill-amber-300 text-amber-300" />
              <span key={score} className="text-sm font-black text-white" style={{ animation: "mbox-score-bump 0.45s ease-out" }}>
                {score}
              </span>
            </Chip>
            {scorePops.map((p) => (
              <span
                key={p.id}
                className="pointer-events-none absolute right-2 top-0 whitespace-nowrap text-sm font-black text-amber-300 drop-shadow-[0_0_8px_rgba(252,211,77,0.9)]"
                style={{ animation: "lab-score-pop 1.4s ease-out forwards" }}
              >
                +{p.amount} ⭐
              </span>
            ))}
          </div>

          <Chip className="!px-2.5 !py-1">
            {Array.from({ length: STARTING_LIVES }, (_, i) => {
              const spent = i >= lives;
              const isLast = lives === 1 && i === 0;
              return (
                <Heart
                  key={i}
                  className={`h-3.5 w-3.5 ${spent ? "text-white/20" : "fill-rose-400 text-rose-400"}`}
                  style={{
                    animation: spent
                      ? "lab-life-lost 0.6s ease-out forwards"
                      : isLast
                        ? 
                          
                          "lab-life-last 2.2s ease-in-out infinite"
                        : undefined,
                  }}
                />
              );
            })}
          </Chip>
        </div>
      </div>

      {}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-40 px-3 pb-3 sm:px-6 sm:pb-4">
        <div className="mx-auto flex w-full max-w-2xl items-center gap-1.5 sm:gap-2">
          {STATIONS.map((name, i) => {
            const done = i < currentStation;
            const here = i === currentStation;
            return (
              <div key={name} className="flex flex-1 flex-col items-center gap-1">
                <div className="flex w-full items-center gap-1">
                  <span
                    className={`h-2 w-2 shrink-0 rounded-full transition-colors duration-500 ${
                      done ? "bg-cyan-300" : here ? "bg-cyan-200" : "bg-white/20"
                    }`}
                    style={{
                      animation: here ? "lab-station-active 1.8s ease-in-out infinite" : undefined,
                      boxShadow: done || here ? "0 0 10px rgba(103,232,249,0.9)" : undefined,
                    }}
                  />
                  {i < STATIONS.length - 1 && (
                    <span
                      className={`h-px flex-1 transition-colors duration-500 ${done ? "bg-cyan-300/70" : "bg-white/15"}`}
                    />
                  )}
                </div>
                <span
                  className={`hidden truncate text-[9px] font-semibold transition-colors duration-500 sm:block ${
                    here ? "text-cyan-200" : done ? "text-white/60" : "text-white/25"
                  }`}
                >
                  {name}
                </span>
              </div>
            );
          })}
        </div>

        {}
        <div className="mx-auto mt-2 h-1 w-full max-w-2xl overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </>
  );
}
