"use client";

import { useState } from "react";
import { GamePhase, GameResult, Difficulty, Round, GameTemplate } from "./types";
import { materialsApi } from "@/lib/api";
import StartScreen from "./StartScreen";
import SoloGame from "./SoloGame";
import DuelGame from "./DuelGame";
import ResultScreen from "./ResultScreen";

/** The state machine wiring start → solo/duel → result together — each
 * screen is otherwise a self-contained component (see their own doc
 * comments), this just owns which one is on screen and what the last run's
 * settings were (so "Играть снова" can relaunch the same mode without
 * re-asking). Rendered by GamePlayer.tsx inside a fixed full-viewport
 * overlay, so from here down every screen can assume it owns the whole
 * screen. */
export default function GameEngine({
  title,
  rounds,
  materialId,
  initialTemplate,
  onClose,
  onRegenerate,
  regenerating,
}: {
  title: string;
  rounds: Round[];
  /** Needed to save each run's result (see finishRun below) and to fetch
   * this account's past runs for StartScreen's "Ваши лучшие результаты". */
  materialId: string;
  /** Pre-picked from GamePlayer.tsx's own Blooket-style gallery cover —
   * when set, StartScreen skips its own template-picking step and opens
   * straight on mode (1/2 players), since the choice was already made
   * before this overlay even opened. */
  initialTemplate?: GameTemplate;
  onClose: () => void;
  /** Rerolls a fresh 12-round set on the same topic (see GamePlayer.tsx's
   * `regenerate`) — resolves once `rounds` above has actually been
   * replaced, so heading back to "start" afterwards is guaranteed to pick
   * up the new set rather than racing the update. */
  onRegenerate: () => Promise<void>;
  regenerating: boolean;
}) {
  const [phase, setPhase] = useState<GamePhase>("start");
  const [lastDifficulty, setLastDifficulty] = useState<Difficulty>("medium");
  const [template, setTemplate] = useState<GameTemplate>(initialTemplate ?? "classic");
  const [result, setResult] = useState<GameResult | null>(null);
  // Bumped every time a run finishes so StartScreen's "Ваши лучшие
  // результаты" re-fetches instead of showing a stale list from before
  // this run was saved.
  const [attemptsVersion, setAttemptsVersion] = useState(0);

  function startSolo(difficulty: Difficulty, tpl: GameTemplate) {
    setLastDifficulty(difficulty);
    setTemplate(tpl);
    setPhase("solo");
  }

  function startDuel(tpl: GameTemplate) {
    setTemplate(tpl);
    setPhase("duel");
  }

  function finishRun(r: GameResult) {
    setResult(r);
    setPhase("result");
    const body =
      r.mode === "solo"
        ? {
            mode: "solo" as const,
            score: r.score,
            won: r.won,
            rounds_cleared: r.roundsCleared,
            total_rounds: r.totalRounds,
            max_streak: r.maxStreak,
          }
        : {
            mode: "duel" as const,
            score: Math.max(r.scoreP1, r.scoreP2),
            score_p1: r.scoreP1,
            score_p2: r.scoreP2,
            won: r.winner !== 0,
            rounds_cleared: rounds.length,
            total_rounds: rounds.length,
            max_streak: 0,
          };
    // Fire-and-forget: a failed save shouldn't block the result screen the
    // pupil is already looking at — same tolerance TestPlayer's own
    // submitTestAttempt failure has (it just shows "couldn't save").
    materialsApi
      .submitGameAttempt(materialId, body)
      .then(() => setAttemptsVersion((v) => v + 1))
      .catch(() => {});
  }

  // "New questions for the next pupil" — a fresh set on the same topic
  // instead of the exact rounds whoever just played already saw. Goes back
  // to the start screen (not straight into a mode) since it's meant for
  // handing the device to a different kid, who should get their own
  // 1-player/2-player choice rather than inheriting the last run's.
  async function regenerateAndReset() {
    await onRegenerate();
    setPhase("start");
  }

  return (
    <div className="h-full w-full">
      {phase === "start" && (
        <StartScreen
          title={title}
          totalRounds={rounds.length}
          materialId={materialId}
          attemptsVersion={attemptsVersion}
          initialTemplate={initialTemplate}
          onStartSolo={startSolo}
          onStartDuel={startDuel}
          onClose={onClose}
        />
      )}
      {phase === "solo" && <SoloGame rounds={rounds} difficulty={lastDifficulty} template={template} onFinish={finishRun} />}
      {phase === "duel" && <DuelGame rounds={rounds} template={template} onFinish={finishRun} />}
      {phase === "result" && result && (
        <ResultScreen
          result={result}
          template={template}
          onPlayAgain={() => setPhase(result.mode === "solo" ? "solo" : "duel")}
          onMainMenu={() => setPhase("start")}
          onNewQuestions={regenerateAndReset}
          regenerating={regenerating}
        />
      )}
    </div>
  );
}
