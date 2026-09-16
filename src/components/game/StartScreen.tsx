"use client";

import { useEffect, useState } from "react";
import { Gamepad2, User, Users, X, Zap, Trophy, Target, Percent } from "lucide-react";
import { Difficulty, DIFFICULTY_CONFIG, GameTemplate, TEMPLATE_META } from "./types";
import { TemplateScene } from "./templates";
import { sfx } from "./sound";
import { materialsApi, GameAttemptOut } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useT } from "@/lib/i18n";
import { LEVEL_LABEL_KEYS } from "@/lib/material-types";

const TEMPLATES: GameTemplate[] = ["classic", "race", "goldrush", "battle", "classroom"];





const CARD_STYLE: Record<GameTemplate, { card: string; badge: string }> = {
  classic: { card: "bg-white/10 hover:bg-white", badge: "bg-white/15" },
  race: { card: "border border-[#ffb86b]/25 bg-[#3a3f6b]/50 hover:bg-white", badge: "bg-[#ffb86b]/25" },
  goldrush: { card: "border border-amber-400/25 bg-[#4a2f0f]/50 hover:bg-white", badge: "bg-amber-400/25" },
  battle: { card: "border border-red-500/25 bg-[#3a0a0a]/50 hover:bg-white", badge: "bg-red-500/25" },
  classroom: { card: "border border-emerald-400/25 bg-[#0f3226]/50 hover:bg-white", badge: "bg-emerald-400/25" },
};








export default function StartScreen({
  title,
  totalRounds,
  materialId,
  attemptsVersion,
  initialTemplate,
  onStartSolo,
  onStartDuel,
  onClose,
}: {
  title: string;
  totalRounds: number;
  
  materialId: string;
  
  attemptsVersion: number;
  
  initialTemplate?: GameTemplate;
  onStartSolo: (difficulty: Difficulty, template: GameTemplate) => void;
  onStartDuel: (template: GameTemplate) => void;
  onClose: () => void;
}) {
  const [picking, setPicking] = useState<"template" | "mode" | "difficulty">(initialTemplate ? "mode" : "template");
  const [template, setTemplate] = useState<GameTemplate>(initialTemplate ?? "classic");
  const t = useT();
  const { user } = useAuth();
  const [attempts, setAttempts] = useState<GameAttemptOut[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    materialsApi
      .listGameAttempts(materialId)
      .then((rows) => {
        if (!cancelled) setAttempts(rows);
      })
      .catch(() => {
        if (!cancelled) setAttempts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [materialId, attemptsVersion]);

  
  
  
  
  
  
  return (
    <TemplateScene template={template}>
    <div className="relative flex h-full w-full flex-1 flex-col items-center overflow-y-auto px-4 pb-6 pt-4 text-center">
      {}
      {user && (
        <div className="mb-2 flex w-full max-w-xs items-center gap-2 self-start rounded-2xl bg-white/10 px-3 py-2 text-left shadow-lg shadow-black/20 backdrop-blur-sm">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-white/40 to-white/10 text-xs font-extrabold text-white ring-2 ring-white/30">
            {user.full_name.trim().charAt(0).toUpperCase() || "?"}
          </span>
          <span className="min-w-0 truncate text-xs font-semibold text-white/90">{user.full_name}</span>
        </div>
      )}

      <button
        onClick={onClose}
        className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 text-white backdrop-blur-sm transition hover:bg-white/25"
        aria-label={t("game.close")}
      >
        <X className="h-4 w-4" />
      </button>

      <div className="flex flex-1 flex-col items-center justify-center">
      <div className="relative flex h-20 w-20 items-center justify-center" style={{ animation: "mascot-bob 2.8s ease-in-out infinite" }}>
        <span className="absolute inset-0 rounded-3xl bg-white/20 blur-xl" aria-hidden />
        <span className="relative flex h-full w-full items-center justify-center rounded-3xl bg-white/15 shadow-lg shadow-black/20 backdrop-blur-sm">
          <Gamepad2 className="h-10 w-10 text-white" />
        </span>
      </div>

      <h1 className="relative mt-5 max-w-sm text-2xl font-extrabold leading-tight text-white drop-shadow-md sm:text-3xl">{title}</h1>
      <p className="relative mt-2 inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/80 shadow-sm backdrop-blur-sm">
        {totalRounds} {t("game.roundsAwait")}
      </p>

      <div className="relative mt-10 w-full max-w-xs">
        {picking === "template" && (
          <div key="template" style={{ animation: "game-round-in 0.35s ease-out" }}>
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-white/60">{t("game.selectTemplate")}</p>
            <div className="grid grid-cols-2 gap-2.5">
              {TEMPLATES.map((tpl) => {
                const meta = TEMPLATE_META[tpl];
                const style = CARD_STYLE[tpl];
                return (
                  <button
                    key={tpl}
                    onClick={() => {
                      sfx.click();
                      setTemplate(tpl);
                      setPicking("mode");
                    }}
                    className={`group flex flex-col items-center gap-2 rounded-2xl px-3 py-4 text-center shadow-lg shadow-black/10 backdrop-blur-sm transition hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0 ${style.card}`}
                  >
                    <span className="text-xs font-extrabold tracking-wide text-white group-hover:text-[#4c1d95]">{meta.label}</span>
                    <span className="text-[10px] leading-tight text-white/60 group-hover:text-[#6d28d9]">{meta.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {picking === "mode" && (
          <div key="mode" className="space-y-3" style={{ animation: "game-round-in 0.35s ease-out" }}>
            <ModeButton
              variant="solo"
              icon={<User className="h-5 w-5" />}
              label={t("game.player1Label")}
              sub={t("game.player1Sub")}
              onClick={() => {
                sfx.click();
                setPicking("difficulty");
              }}
            />
            <ModeButton
              variant="duel"
              icon={<Users className="h-5 w-5" />}
              label={t("game.player2Label")}
              sub={t("game.player2Sub")}
              onClick={() => {
                sfx.click();
                onStartDuel(template);
              }}
            />
            <button
              onClick={() => (initialTemplate ? onClose() : setPicking("template"))}
              className="mx-auto mt-1 block text-xs font-medium text-white/60 underline-offset-4 hover:text-white/90 hover:underline"
            >
              ← {TEMPLATE_META[template].emoji} {TEMPLATE_META[template].label}
            </button>

            <StatsPanel attempts={attempts} />
          </div>
        )}

        {picking === "difficulty" && (
          <div key="difficulty" className="space-y-3" style={{ animation: "game-round-in 0.35s ease-out" }}>
            {(Object.keys(DIFFICULTY_CONFIG) as Difficulty[]).map((d) => (
              <ModeButton
                key={d}
                variant={d}
                icon={<Zap className="h-5 w-5" />}
                label={t(LEVEL_LABEL_KEYS[DIFFICULTY_CONFIG[d].label]).toUpperCase()}
                sub={t(
                  d === "easy" ? "game.difficultyEasySub" : d === "medium" ? "game.difficultyMediumSub" : "game.difficultyHardSub"
                )}
                onClick={() => {
                  sfx.click();
                  onStartSolo(d, template);
                }}
              />
            ))}
            <button
              onClick={() => setPicking("mode")}
              className="mx-auto mt-1 block text-xs font-medium text-white/60 underline-offset-4 hover:text-white/90 hover:underline"
            >
              ← {t("common.back")}
            </button>
          </div>
        )}
      </div>
      </div>
    </div>
    </TemplateScene>
  );
}


function StatsPanel({ attempts }: { attempts: GameAttemptOut[] | null }) {
  const t = useT();
  if (!attempts || attempts.length === 0) return null;

  const gamesPlayed = attempts.length;
  const bestScore = Math.max(...attempts.map((a) => a.score));
  const winRate = Math.round((attempts.filter((a) => a.won).length / gamesPlayed) * 100);
  const top3 = [...attempts].sort((a, b) => b.score - a.score).slice(0, 3);

  return (
    <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
      <div className="grid grid-cols-3 gap-2">
        <Stat icon={<Target className="h-3.5 w-3.5" />} color="bg-sky-500/25 text-sky-200" label={t("game.statGames")} value={gamesPlayed} />
        <Stat icon={<Trophy className="h-3.5 w-3.5" />} color="bg-amber-500/25 text-amber-200" label={t("game.statRecord")} value={bestScore} />
        <Stat icon={<Percent className="h-3.5 w-3.5" />} color="bg-emerald-500/25 text-emerald-200" label={t("game.statWinRate")} value={`${winRate}%`} />
      </div>
      <div>
        <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-white/50">{t("game.bestResults")}</p>
        <div className="space-y-1">
          {top3.map((a, i) => (
            <div key={a.id} className="flex items-center justify-between rounded-lg bg-white/5 px-2.5 py-1.5 text-xs">
              <span className="flex items-center gap-1.5 text-white/70">
                <span className="w-3 text-white/40">{i + 1}.</span>
                {a.mode === "duel" ? `P1 ${a.score_p1} · P2 ${a.score_p2}` : t("game.solo")}
              </span>
              <span className="font-bold text-white">{a.score}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number | string; color: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl bg-white/5 py-2.5">
      <span className={`flex h-7 w-7 items-center justify-center rounded-full ${color}`}>{icon}</span>
      <span className="text-sm font-extrabold text-white">{value}</span>
      <span className="text-[9px] uppercase tracking-wide text-white/50">{label}</span>
    </div>
  );
}





const MODE_BUTTON_STYLE = {
  solo: "bg-gradient-to-br from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500",
  duel: "bg-gradient-to-br from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500",
  easy: "bg-gradient-to-br from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500",
  medium: "bg-gradient-to-br from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500",
  hard: "bg-gradient-to-br from-red-500 to-rose-600 hover:from-red-400 hover:to-rose-500",
} as const;

function ModeButton({
  icon,
  label,
  sub,
  onClick,
  variant,
}: {
  icon: React.ReactNode;
  label: string;
  sub: string;
  onClick: () => void;
  variant: keyof typeof MODE_BUTTON_STYLE;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex w-full items-center gap-3 rounded-2xl px-4 py-3.5 text-left shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0 active:scale-[0.98] active:shadow-md ${MODE_BUTTON_STYLE[variant]}`}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/20 text-white">{icon}</span>
      <span>
        <span className="block text-sm font-extrabold tracking-wide text-white">{label}</span>
        <span className="block text-xs text-white/80">{sub}</span>
      </span>
    </button>
  );
}
