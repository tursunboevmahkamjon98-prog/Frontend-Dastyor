"use client";

import { Flag, Coins, Swords, Star, Apple } from "lucide-react";
import { GameTemplate } from "./types";
















export function TemplateScene({ template, children }: { template: GameTemplate; children: React.ReactNode }) {
  if (template === "race") {
    return (
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-gradient-to-b from-[#1a2b4a] via-[#3a3f6b] to-[#12101f]">
        <div className="pointer-events-none absolute -top-16 right-1/4 h-56 w-56 rounded-full bg-[#ffb86b]/30 blur-3xl" style={{ animation: "game-float 8s ease-in-out infinite" }} />
        <div className="pointer-events-none absolute left-0 top-1/3 h-32 w-full bg-white/5 blur-2xl" />
        <div className="pointer-events-none absolute bottom-0 left-0 h-24 w-full bg-gradient-to-t from-black/50 to-transparent" />
        <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
      </div>
    );
  }
  if (template === "goldrush") {
    return (
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-gradient-to-b from-[#2a1a08] via-[#4a2f0f] to-[#1a0f05]">
        <div className="pointer-events-none absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-[#fbbf24]/25 blur-3xl" style={{ animation: "game-float 7s ease-in-out infinite" }} />
        <div className="pointer-events-none absolute -bottom-10 -right-10 h-56 w-56 rounded-full bg-[#f59e0b]/15 blur-3xl" style={{ animation: "game-float 9s ease-in-out infinite reverse" }} />
        <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
      </div>
    );
  }
  if (template === "battle") {
    return (
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-gradient-to-b from-[#2a0808] via-[#1a0505] to-[#0a0000]">
        <div className="pointer-events-none absolute left-1/2 top-1/4 h-64 w-64 -translate-x-1/2 rounded-full bg-red-600/25 blur-3xl" style={{ animation: "game-urgent-pulse 2.4s ease-in-out infinite" }} />
        <div className="pointer-events-none absolute bottom-0 left-0 h-1 w-full bg-red-500/40 blur-sm" />
        <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
      </div>
    );
  }
  if (template === "classroom") {
    
    
    
    
    
    
    
    
    return (
      <div className="relative flex h-full w-full flex-col overflow-hidden bg-[#0f3226]">
        {}
        <img
          src="/game-backgrounds/classroom.png"
          alt=""
          className="pointer-events-none absolute inset-0 h-full w-full object-cover"
          style={{ animation: "game-kenburns 25s ease-in-out infinite alternate" }}
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/60 via-black/45 to-black/65" />
        <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
      </div>
    );
  }
  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden bg-gradient-to-b from-[#2e1065] to-[#4c1d95]">
      <div className="pointer-events-none absolute -left-10 -top-10 h-64 w-64 rounded-full bg-white/5 blur-3xl" style={{ animation: "game-float 7s ease-in-out infinite" }} />
      <div className="relative z-10 flex h-full w-full flex-1 flex-col">{children}</div>
    </div>
  );
}


export function SoloProgress({ template, pct }: { template: GameTemplate; pct: number }) {
  const clamped = Math.max(0, Math.min(1, pct));
  if (template === "race") return <RaceTrack pct={clamped} />;
  if (template === "goldrush") return <GoldPile pct={clamped} />;
  if (template === "battle") return <BattleBar pct={clamped} />;
  if (template === "classroom") return <ChalkTrack pct={clamped} />;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className="h-full rounded-full bg-gradient-to-r from-amber-300 to-fuchsia-400 transition-all duration-500"
        style={{ width: `${clamped * 100}%` }}
      />
    </div>
  );
}


function RaceTrack({ pct }: { pct: number }) {
  return (
    <div className="relative h-9 w-full overflow-hidden rounded-full border border-white/10 bg-[repeating-linear-gradient(90deg,rgba(255,255,255,0.08)_0px,rgba(255,255,255,0.08)_18px,transparent_18px,transparent_36px)] bg-[#2b2440]">
      <Flag className="absolute right-1.5 top-1/2 h-4 w-4 -translate-y-1/2 text-amber-300" />
      <div
        className="absolute top-1/2 -translate-y-1/2 text-xl transition-all duration-700 ease-out"
        style={{ left: `calc(${pct * 100}% * 0.86)`, animation: "game-car-bob 0.5s ease-in-out infinite" }}
      >
        🏎️
      </div>
    </div>
  );
}

function GoldPile({ pct }: { pct: number }) {
  const coinCount = Math.min(10, Math.round(pct * 10));
  return (
    <div className="flex h-9 w-full items-center gap-1.5 overflow-hidden rounded-full border border-amber-400/20 bg-[#2b2440] px-3">
      <Coins className="h-4 w-4 shrink-0 text-amber-300" />
      <div className="flex flex-1 items-center gap-0.5 overflow-hidden">
        {Array.from({ length: 10 }, (_, i) => (
          <span
            key={i}
            className={`text-sm transition-all duration-300 ${i < coinCount ? "scale-100 opacity-100" : "scale-0 opacity-0"}`}
            style={{ animation: i === coinCount - 1 ? "game-coin-drop 0.4s ease-out" : undefined }}
          >
            🪙
          </span>
        ))}
      </div>
    </div>
  );
}




function ChalkTrack({ pct }: { pct: number }) {
  return (
    <div className="relative h-9 w-full overflow-hidden rounded-full border-2 border-dashed border-white/25 bg-[#081f18]">
      <div className="absolute inset-y-0 left-0 rounded-full bg-white/10 transition-all duration-500" style={{ width: `${pct * 100}%` }} />
      <div
        className="absolute top-1/2 -translate-y-1/2 text-lg transition-all duration-700 ease-out"
        style={{ left: `calc(${pct * 100}% * 0.9)` }}
      >
        🍎
      </div>
    </div>
  );
}

function BattleBar({ pct }: { pct: number }) {
  
  
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-base">🧌</span>
      <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-red-500 to-red-400 transition-all duration-500"
          style={{ width: `${(1 - pct) * 100}%` }}
        />
      </div>
      <Swords className="h-4 w-4 shrink-0 text-red-300" />
    </div>
  );
}


export function DuelHud({
  template,
  scoreP1,
  scoreP2,
  totalRounds,
  roundLabel,
}: {
  template: GameTemplate;
  scoreP1: number;
  scoreP2: number;
  totalRounds: number;
  roundLabel: React.ReactNode;
}) {
  const p1 = totalRounds > 0 ? scoreP1 / totalRounds : 0;
  const p2 = totalRounds > 0 ? scoreP2 / totalRounds : 0;

  if (template === "race") {
    return (
      <div className="flex flex-col gap-1.5 px-4 py-2">
        <DuelRaceLane pct={p1} label="P1" color="text-sky-300" />
        <div className="text-center text-[11px] text-white/50">{roundLabel}</div>
        <DuelRaceLane pct={p2} label="P2" color="text-pink-300" />
      </div>
    );
  }
  if (template === "goldrush") {
    return (
      <div className="flex items-center justify-between px-4 py-2">
        <DuelGoldChip score={scoreP1} label="P1" color="text-sky-300" />
        <div className="text-center text-[11px] text-white/50">{roundLabel}</div>
        <DuelGoldChip score={scoreP2} label="P2" color="text-pink-300" />
      </div>
    );
  }
  if (template === "battle") {
    return (
      <div className="flex items-center gap-3 px-4 py-2">
        <DuelHpBar pct={1 - p2} label="P1" color="bg-sky-400" />
        <Swords className="h-4 w-4 shrink-0 text-white/50" />
        <DuelHpBar pct={1 - p1} label="P2" color="bg-pink-400" reverse />
      </div>
    );
  }
  if (template === "classroom") {
    return (
      <div className="flex items-center justify-between px-4 py-2 text-white">
        <DeskChip score={scoreP1} color="text-sky-300" />
        <div className="text-center text-[11px] text-white/50">{roundLabel}</div>
        <DeskChip score={scoreP2} color="text-pink-300" />
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between px-4 py-2 text-white">
      <ClassicChip score={scoreP1} color="text-sky-300" bg="bg-sky-500/20" />
      <div className="text-center">{roundLabel}</div>
      <ClassicChip score={scoreP2} color="text-pink-300" bg="bg-pink-500/20" />
    </div>
  );
}

function DuelRaceLane({ pct, label, color }: { pct: number; label: string; color: string }) {
  return (
    <div className="relative h-6 w-full overflow-hidden rounded-full border border-white/10 bg-[repeating-linear-gradient(90deg,rgba(255,255,255,0.08)_0px,rgba(255,255,255,0.08)_14px,transparent_14px,transparent_28px)] bg-[#2b2440]">
      <span className={`absolute left-1.5 top-1/2 -translate-y-1/2 text-[9px] font-bold ${color}`}>{label}</span>
      <Flag className="absolute right-1 top-1/2 h-3 w-3 -translate-y-1/2 text-amber-300" />
      <span
        className="absolute top-1/2 -translate-y-1/2 text-sm transition-all duration-700 ease-out"
        style={{ left: `calc(${Math.min(1, pct) * 100}% * 0.9)` }}
      >
        🏎️
      </span>
    </div>
  );
}

function DuelGoldChip({ score, label, color }: { score: number; label: string; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-[10px] font-bold ${color}`}>{label}</span>
      <Coins className="h-3.5 w-3.5 text-amber-300" />
      <span key={score} className="text-sm font-extrabold text-white" style={{ animation: "game-pop 0.3s ease-out" }}>
        {score}
      </span>
    </div>
  );
}

function DuelHpBar({ pct, label, color, reverse }: { pct: number; label: string; color: string; reverse?: boolean }) {
  const clamped = Math.max(0, Math.min(1, pct));
  return (
    <div className={`flex flex-1 items-center gap-1.5 ${reverse ? "flex-row-reverse" : ""}`}>
      <span className="shrink-0 text-[10px] font-bold text-white/70">{label}</span>
      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${clamped * 100}%`, marginLeft: reverse ? "auto" : undefined }}
        />
      </div>
    </div>
  );
}

function DeskChip({ score, color }: { score: number; color: string }) {
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-3 py-1.5">
      <Apple className={`h-3.5 w-3.5 ${color}`} />
      <span key={score} className="text-base font-extrabold text-white" style={{ animation: "game-pop 0.3s ease-out" }}>
        {score}
      </span>
    </div>
  );
}

function ClassicChip({ score, color, bg }: { score: number; color: string; bg: string }) {
  return (
    <div className={`flex items-center gap-2 rounded-full px-3 py-1.5 ${bg}`}>
      <Star className={`h-3.5 w-3.5 ${color}`} />
      <span key={score} className="text-base font-extrabold text-white" style={{ animation: "game-pop 0.3s ease-out" }}>
        {score}
      </span>
    </div>
  );
}
