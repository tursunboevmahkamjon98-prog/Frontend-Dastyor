"use client";

import { useEffect, useState } from "react";
import { Check, FlaskConical, Home, RotateCcw, Star, X } from "lucide-react";
import { Confetti } from "../game/effects";

interface Stat {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  tint: string;
}


export default function LabResultScreen({
  score,
  correctCount,
  wrongCount,
  roundsPlayed,
  outOfLives,
  onReplay,
  onExit,
}: {
  score: number;
  correctCount: number;
  wrongCount: number;
  roundsPlayed: number;
  
  outOfLives: boolean;
  onReplay: () => void;
  onExit: () => void;
}) {
  const stats: Stat[] = [
    { icon: <Star className="h-4 w-4" />, label: "Хол", value: score, tint: "text-amber-300" },
    { icon: <Check className="h-4 w-4" />, label: "Ҷавобҳои дуруст", value: correctCount, tint: "text-emerald-300" },
    { icon: <X className="h-4 w-4" />, label: "Ҷавобҳои нодуруст", value: wrongCount, tint: "text-rose-300" },
    { icon: <FlaskConical className="h-4 w-4" />, label: "Таҷрибаҳои анҷомёфта", value: roundsPlayed, tint: "text-cyan-300" },
  ];

  
  
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (shown >= stats.length) return;
    const id = window.setTimeout(() => setShown((n) => n + 1), 480);
    return () => window.clearTimeout(id);
  }, [shown, stats.length]);

  const celebrating = !outOfLives || correctCount > 0;

  return (
    <div className="relative flex h-full w-full flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-8 text-center">
      {celebrating && <Confetti />}

      <div className="relative" style={{ animation: "mbox-trophy-in 0.8s cubic-bezier(0.3,1.4,0.6,1)" }}>
        <span className="pointer-events-none absolute -inset-8 rounded-full bg-cyan-400/30 blur-3xl" aria-hidden />
        <span className="relative text-6xl">{celebrating ? "🏆" : "🧪"}</span>
      </div>

      <h1 className="relative mt-3 text-2xl font-black text-white drop-shadow-[0_2px_12px_rgba(56,189,248,0.6)] sm:text-3xl">
        {outOfLives ? "Таҷриба ба анҷом расид" : "Табрик мекунем! 🎉"}
      </h1>
      {!outOfLives && (
        <p className="relative mt-1.5 text-sm font-semibold text-cyan-200">Шумо таҷрибаро бомуваффақият анҷом додед!</p>
      )}

      <div className="relative mt-6 grid w-full max-w-md grid-cols-2 gap-2.5">
        {stats.map((s, i) => (
          <div
            key={s.label}
            className="rounded-2xl border border-white/15 bg-white/[0.07] px-3 py-3 shadow-lg backdrop-blur-md"
            style={{
              
              
              opacity: i < shown ? 1 : 0,
              animation: i < shown ? "lab-stat-in 0.5s cubic-bezier(0.22,1,0.36,1)" : undefined,
            }}
          >
            <span className={`mx-auto mb-1 flex h-8 w-8 items-center justify-center rounded-full bg-white/10 ${s.tint}`}>
              {s.icon}
            </span>
            <p className="text-xl font-black text-white">{s.value}</p>
            <p className="mt-0.5 text-[9px] font-semibold uppercase leading-tight tracking-wide text-white/55">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="relative mt-6 flex w-full max-w-md flex-col gap-2.5 sm:flex-row">
        <button
          type="button"
          onClick={onReplay}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 px-4 py-3.5 text-sm font-black text-white shadow-[0_6px_0_rgba(30,64,175,0.9)] transition hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_2px_0_rgba(30,64,175,0.9)]"
        >
          <RotateCcw className="h-4 w-4" />
          Аз нав бозӣ кардан
        </button>
        <button
          type="button"
          onClick={onExit}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-4 py-3.5 text-sm font-bold text-white backdrop-blur-md transition hover:bg-white/20 active:scale-[0.98]"
        >
          <Home className="h-4 w-4" />
          Ба шаблонҳо баргаштан
        </button>
      </div>
    </div>
  );
}
