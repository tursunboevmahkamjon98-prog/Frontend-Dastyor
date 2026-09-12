"use client";

import { useEffect } from "react";
import { Trophy, RotateCcw, Home, Award, Flame, Target, Sparkles, Loader2 } from "lucide-react";
import { GameResult, GameTemplate } from "./types";
import { TemplateScene } from "./templates";
import { Confetti } from "./effects";
import { sfx } from "./sound";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/messages";

const BADGE_META: Record<string, { emoji: string; key: MessageKey }> = {
  perfect: { emoji: "💎", key: "game.badgePerfect" },
  streak: { emoji: "🔥", key: "game.badgeStreak" },
  speedster: { emoji: "⚡", key: "game.badgeSpeedster" },
  survivor: { emoji: "🛡️", key: "game.badgeSurvivor" },
};


// The "победа/поражение" screen for both modes — one component branching on
// result.mode rather than two near-identical screens, since the shared shell
// (confetti/trophy hero + score card + the two footer actions) is the same;
// only the middle stat block differs.
export default function ResultScreen({
  result,
  template,
  onPlayAgain,
  onMainMenu,
  onNewQuestions,
  regenerating,
}: {
  result: GameResult;
  /** Same template the round itself just played in — this screen used to
   * always be one fixed violet gradient regardless, so finishing a
   * "Урок"-themed run would suddenly cut to a purple screen that
   * didn't look like anything the pupil had just seen. */
  template: GameTemplate;
  onPlayAgain: () => void;
  onMainMenu: () => void;
  /** Rerolls a fresh 12-round set on the same topic — for handing the
   * device to a different pupil without the teacher leaving this game to
   * build a whole new material (see GamePlayer.tsx's `regenerate`). */
  onNewQuestions: () => void;
  regenerating: boolean;
}) {
  const t = useT();
  const won = result.mode === "solo" ? result.won : result.winner !== 0;

  useEffect(() => {
    if (won) sfx.win();
    else sfx.lose();
  }, [won]);

  return (
    <TemplateScene template={template}>
    <div className="relative flex h-full w-full flex-1 flex-col items-center justify-center overflow-hidden px-4 text-center">
      {won && <Confetti />}

      <div
        className="relative flex h-24 w-24 items-center justify-center rounded-full bg-white/15 shadow-xl shadow-black/10 backdrop-blur-sm"
        style={{ animation: won ? "mascot-celebrate 0.7s ease-in-out infinite" : undefined }}
      >
        <Trophy className={`h-12 w-12 ${won ? "text-amber-300" : "text-white/70"}`} />
      </div>

      <h1 className="relative mt-5 text-2xl font-extrabold text-white sm:text-3xl">
        {result.mode === "solo"
          ? result.won
            ? t("game.victory")
            : t("game.gameOver")
          : result.winner === 0
            ? t("game.tie")
            : `${t("game.playerWonPrefix")} ${result.winner}! 🏆`}
      </h1>

      <div className="relative mt-6 w-full max-w-sm rounded-3xl bg-white/10 p-5 backdrop-blur-sm">
        {result.mode === "solo" ? (
          <>
            <div className="grid grid-cols-3 gap-3 text-white">
              <Stat icon={<Target className="h-4 w-4" />} label={t("game.statScore")} value={result.score} />
              <Stat icon={<Award className="h-4 w-4" />} label={t("game.statLevel")} value={result.level} />
              <Stat icon={<Flame className="h-4 w-4" />} label={t("game.statStreak")} value={result.maxStreak} />
            </div>
            <p className="mt-4 text-xs text-white/70">
              {t("game.roundsCleared")} {result.roundsCleared} / {result.totalRounds}
            </p>
            {result.badges.length > 0 && (
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {result.badges.map((b, i) => (
                  <span
                    key={b}
                    className="flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-xs font-semibold text-white"
                    style={{ animation: `mascot-pop 0.5s ease-out ${i * 0.1}s backwards` }}
                  >
                    <span className="text-sm">{BADGE_META[b]?.emoji ?? "🏅"}</span>
                    {BADGE_META[b] ? t(BADGE_META[b].key) : b}
                  </span>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-around text-white">
            <PlayerScore n={1} score={result.scoreP1} won={result.winner === 1} />
            <div className="text-lg font-black text-white/40">VS</div>
            <PlayerScore n={2} score={result.scoreP2} won={result.winner === 2} />
          </div>
        )}
      </div>

      <div className="relative mt-8 flex w-full max-w-sm gap-3">
        <button
          onClick={onPlayAgain}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-bold text-slate-800 shadow-lg transition hover:-translate-y-0.5"
        >
          <RotateCcw className="h-4 w-4" />
          {t("game.playAgain")}
        </button>
        <button
          onClick={onMainMenu}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-white/15 px-4 py-3 text-sm font-semibold text-white backdrop-blur-sm transition hover:bg-white/25"
        >
          <Home className="h-4 w-4" />
          {t("game.mainMenu")}
        </button>
      </div>

      {/* For handing the device to the next pupil — same topic, a fresh
          set of 12 rounds instead of the ones just played (see
          GameEngine.tsx's regenerateAndReset), rather than the teacher
          having to leave and generate a whole new game. Kept visually
          quieter than the two actions above: it's a nice-to-have for a
          specific moment (a class taking turns), not the default next step. */}
      <button
        onClick={onNewQuestions}
        disabled={regenerating}
        className="relative mt-4 flex items-center gap-1.5 text-xs font-medium text-white/70 underline-offset-4 transition hover:text-white hover:underline disabled:opacity-60"
      >
        {regenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
        {regenerating ? t("game.newQuestionsPreparing") : t("game.newQuestionsForNext")}
      </button>
    </div>
    </TemplateScene>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="flex flex-col items-center rounded-2xl bg-white/10 py-3">
      <span className="mb-1 text-white/70">{icon}</span>
      <span className="text-lg font-extrabold">{value}</span>
      <span className="text-[10px] uppercase tracking-wide text-white/60">{label}</span>
    </div>
  );
}

function PlayerScore({ n, score, won }: { n: 1 | 2; score: number; won: boolean }) {
  const t = useT();
  return (
    <div className="flex flex-col items-center">
      <span
        className={`flex h-14 w-14 items-center justify-center rounded-full text-lg font-black ${
          won ? "bg-amber-300 text-slate-800" : "bg-white/15 text-white"
        }`}
      >
        P{n}
      </span>
      <span className="mt-2 text-2xl font-extrabold text-white">{score}</span>
      {won && <span className="text-[10px] font-bold uppercase tracking-wide text-amber-300">{t("game.winner")}</span>}
    </div>
  );
}
