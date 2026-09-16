"use client";

import { RotateCcw, Home, Trophy, Target, Percent, Clock, Flame } from "lucide-react";
import { Confetti } from "../game/effects";
import ClownMascot from "./ClownMascot";
import { starsFor } from "./types";

function formatDuration(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}


export default function VictoryScreen({
  score,
  correctAnswers,
  questionsAnswered,
  totalRounds,
  maxStreak,
  elapsedSeconds,
  outOfLives,
  onReplay,
  onNewTopic,
  onExit,
}: {
  score: number;
  correctAnswers: number;
  
  questionsAnswered: number;
  
  totalRounds: number;
  maxStreak: number;
  elapsedSeconds: number;
  
  outOfLives: boolean;
  onReplay: () => void;
  
  onNewTopic: () => void;
  onExit: () => void;
}) {
  
  
  
  const accuracy = questionsAnswered > 0 ? Math.round((correctAnswers / questionsAnswered) * 100) : 0;
  const stars = starsFor(correctAnswers, totalRounds);
  const celebrating = !outOfLives || correctAnswers > 0;

  return (
    <div className="relative flex h-full w-full flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-6 text-center">
      {celebrating && <Confetti />}

      <div className="relative" style={{ animation: "mbox-trophy-in 0.7s cubic-bezier(0.3,1.4,0.6,1)" }}>
        <Trophy className={`h-16 w-16 ${stars >= 3 ? "text-amber-300" : "text-white/70"} drop-shadow-lg`} />
      </div>

      <h1 className="relative mt-3 text-2xl font-black text-white drop-shadow-md sm:text-3xl">
        {outOfLives && correctAnswers === 0 ? "Кӯшиши хуб!" : "Табрик мекунем!"}
      </h1>

      {}
      <div className="relative mt-3 flex gap-1.5">
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={`text-2xl ${i < stars ? "" : "opacity-25 grayscale"}`}
            style={i < stars ? { animation: `mbox-star-land 0.5s ease-out ${0.35 + i * 0.13}s backwards` } : undefined}
          >
            ⭐
          </span>
        ))}
      </div>

      <div className="relative mt-5 w-full max-w-md rounded-3xl border border-white/15 bg-black/35 p-4 shadow-2xl backdrop-blur-md sm:p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-white/60">Холи шумо</p>
        <p className="text-4xl font-black text-white" style={{ animation: "mbox-score-bump 0.6s ease-out 0.3s backwards" }}>
          {score}
        </p>

        <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <Stat icon={<Target className="h-4 w-4" />} label="Ҷавобҳои дуруст" value={`${correctAnswers} / ${questionsAnswered}`} />
          <Stat icon={<Percent className="h-4 w-4" />} label="Дақиқӣ" value={`${accuracy}%`} />
          <Stat icon={<Flame className="h-4 w-4" />} label="Комбои беҳтарин" value={maxStreak} />
          <Stat icon={<Clock className="h-4 w-4" />} label="Вақт" value={formatDuration(elapsedSeconds)} />
        </div>
      </div>

      <div className="relative mt-5 scale-90">
        <ClownMascot mood={celebrating ? "happy" : "sad"} size={140} />
      </div>

      <div className="relative mt-4 flex w-full max-w-md flex-col gap-2.5 sm:flex-row">
        <button
          type="button"
          onClick={onReplay}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 px-4 py-3.5 text-sm font-black text-white shadow-lg transition hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
        >
          <RotateCcw className="h-4 w-4" />
          Аз нав бозӣ кардан
        </button>
        <button
          type="button"
          onClick={onExit}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-white/15 px-4 py-3.5 text-sm font-bold text-white backdrop-blur-sm transition hover:bg-white/25 active:scale-[0.98]"
        >
          <Home className="h-4 w-4" />
          Ба бозиҳо баргаштан
        </button>
      </div>

      <button
        type="button"
        onClick={onNewTopic}
        className="relative mt-3 text-xs font-semibold text-white/70 underline-offset-4 transition hover:text-white hover:underline"
      >
        Мавзӯи нав интихоб кардан
      </button>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="flex flex-col items-center rounded-2xl bg-white/10 px-2 py-2.5">
      <span className="mb-1 text-white/70">{icon}</span>
      <span className="text-base font-black text-white">{value}</span>
      <span className="mt-0.5 text-[9px] uppercase leading-tight tracking-wide text-white/55">{label}</span>
    </div>
  );
}
