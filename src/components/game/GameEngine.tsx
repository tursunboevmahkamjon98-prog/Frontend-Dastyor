"use client";

import { useState } from "react";
import { GamePhase, GameResult, Difficulty, Round, GameTemplate } from "./types";
import { materialsApi } from "@/lib/api";
import StartScreen from "./StartScreen";
import SoloGame from "./SoloGame";
import DuelGame from "./DuelGame";
import ResultScreen from "./ResultScreen";


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
  
  materialId: string;
  
  initialTemplate?: GameTemplate;
  onClose: () => void;
  
  onRegenerate: () => Promise<void>;
  regenerating: boolean;
}) {
  const [phase, setPhase] = useState<GamePhase>("start");
  const [lastDifficulty, setLastDifficulty] = useState<Difficulty>("medium");
  const [template, setTemplate] = useState<GameTemplate>(initialTemplate ?? "classic");
  const [result, setResult] = useState<GameResult | null>(null);
  
  
  
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
    
    
    
    materialsApi
      .submitGameAttempt(materialId, body)
      .then(() => setAttemptsVersion((v) => v + 1))
      .catch(() => {});
  }

  
  
  
  
  
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
