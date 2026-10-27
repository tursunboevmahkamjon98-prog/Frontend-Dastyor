"use client";

import { useEffect, useRef, useState } from "react";
import { X, ArrowRight } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Burst } from "../game/effects";
import ClassroomScene from "./ClassroomScene";
import ClownMascot, { ClownMood } from "./ClownMascot";
import FlyingQuestionCard from "./FlyingQuestionCard";
import MagicBox from "./MagicBox";
import QuestionPanel from "./QuestionPanel";
import ScoreHUD from "./ScoreHUD";
import SetupScreen from "./SetupScreen";
import VictoryScreen from "./VictoryScreen";
import { BOX_COUNT, Phase, ShuffleQuestion, roundConfig } from "./types";
import { useShuffleGame } from "./useShuffleGame";


const SLOT_W_DESKTOP = 150;
const SLOT_W_MOBILE = 106;
const BOX_W = 104;


const MOOD_FOR_PHASE: Record<Phase, ClownMood> = {
  setup: "idle",
  reveal: "reveal",
  lidsOpen: "casting",
  inserting: "casting",
  lidsClose: "casting",
  countdown: "casting",
  shuffling: "shuffling",
  choosing: "waiting",
  opening: "surprised",
  emerging: "surprised",
  question: "waiting",
  feedback: "idle", 
  result: "happy",
};


const CARD_TO_BOX_Y = 190;


export default function MagicShuffleGame({
  defaultSubject,
  defaultTopic,
  defaultGrade,
  onClose,
}: {
  
  defaultSubject?: string;
  defaultTopic?: string;
  defaultGrade?: string;
  onClose: () => void;
}) {
  const game = useShuffleGame();
  const { user } = useAuth();
  const playerName = user?.full_name?.trim() || "Меҳмон";

  
  const [chosenQuestions, setChosenQuestions] = useState<ShuffleQuestion[]>([]);

  
  
  
  const [slotW, setSlotW] = useState(SLOT_W_DESKTOP);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 640px)");
    const apply = () => setSlotW(mq.matches ? SLOT_W_DESKTOP : SLOT_W_MOBILE);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const cfg = roundConfig(game.round);
  const rowWidth = (BOX_COUNT - 1) * slotW + BOX_W;

  const mood: ClownMood =
    game.phase === "feedback" ? (game.answerCorrect ? "happy" : "sad") : MOOD_FOR_PHASE[game.phase];

  
  if (game.phase === "setup") {
    return (
      <ClassroomScene>
        <CloseButton onClose={onClose} />
        <SetupScreen
          defaultSubject={defaultSubject}
          defaultTopic={defaultTopic}
          defaultGrade={defaultGrade}
          onReady={(qs) => {
            
            
            setChosenQuestions(qs);
            game.start(qs);
          }}
        />
      </ClassroomScene>
    );
  }

  
  if (game.phase === "result") {
    return (
      <ClassroomScene>
        <CloseButton onClose={onClose} />
        <VictoryScreen
          score={game.score}
          correctAnswers={game.correctAnswers}
          questionsAnswered={game.questionsAnswered}
          totalRounds={game.totalRounds}
          maxStreak={game.maxStreak}
          elapsedSeconds={game.elapsedSeconds}
          outOfLives={game.lives <= 0}
          onReplay={() => game.start(chosenQuestions)}
          onNewTopic={game.backToSetup}
          onExit={onClose}
        />
      </ClassroomScene>
    );
  }

  
  const lidsUp = game.phase === "lidsOpen" || game.phase === "inserting";
  const lidsClosing = game.phase === "lidsClose";
  const showBoxes = game.phase !== "reveal";
  const boxesInteractive = game.phase === "choosing";

  
  function offsetToSlot(position: number): number {
    return position * slotW + BOX_W / 2 - rowWidth / 2;
  }

  const openedBox = game.boxes.find((b) => b.id === game.pickedBoxId) ?? null;

  
  
  
  
  const cardRestY = game.phase === "emerging" || game.phase === "question" ? -104 : 0;

  return (
    <ClassroomScene>
      <CloseButton onClose={onClose} />
      <ScoreHUD
        playerName={playerName}
        round={game.round}
        totalRounds={game.totalRounds}
        score={game.score}
        lives={game.lives}
        streak={game.streak}
      />

      <div className="relative flex h-full w-full flex-1 flex-col items-center justify-end overflow-hidden px-3 pb-12 pt-16 sm:pb-14">
        {}
        <div className="relative z-20 mb-1 flex flex-col items-center">
          <ClownMascot mood={mood} size={slotW === SLOT_W_DESKTOP ? 170 : 130} />
        </div>

        {}
        {(game.phase === "reveal" || game.phase === "lidsOpen" || game.phase === "lidsClose") && (
          <div className="pointer-events-none absolute inset-x-0 top-[14%] z-40 flex justify-center px-4">
            <span
              key={game.phase}
              className="rounded-2xl bg-black/50 px-5 py-2 text-sm font-black text-amber-200 backdrop-blur-sm sm:text-base"
              style={{ animation: "mascot-pop 0.4s ease-out" }}
            >
              {game.phase === "reveal"
                ? "Саволҳоро бодиққат нигоҳ доред!"
                : game.phase === "lidsOpen"
                  ? "Саволҳо ба қуттиҳо гузошта мешаванд..."
                  : "Қуттиҳо баста шуданд!"}
            </span>
          </div>
        )}

        {}
        {game.phase === "countdown" && (
          <div className="pointer-events-none absolute inset-0 z-40 flex flex-col items-center justify-center gap-3">
            <span
              className="rounded-2xl bg-black/45 px-5 py-2 text-sm font-black text-amber-200 backdrop-blur-sm sm:text-base"
              style={{ animation: "mascot-pop 0.4s ease-out" }}
            >
              Диққат! Қуттиҳо омехта мешаванд...
            </span>
            <span
              key={game.countdownStep}
              className="text-7xl font-black text-white drop-shadow-[0_4px_0_rgba(0,0,0,0.4)] sm:text-8xl"
              style={{ animation: "mascot-pop 0.45s ease-out" }}
            >
              {game.countdownStep > 0 ? game.countdownStep : "Биёед!"}
            </span>
          </div>
        )}

        {}
        {game.comboToast && (
          <div className="pointer-events-none absolute inset-x-0 top-1/3 z-40 flex justify-center">
            <span
              key={game.comboToast}
              className="rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 px-5 py-2.5 text-lg font-black text-white shadow-2xl"
              style={{ animation: "mbox-toast 2s ease-out forwards" }}
            >
              {game.comboToast}
            </span>
          </div>
        )}

        {}
        {showBoxes && (
          <div className="relative z-10 h-[150px] shrink-0" style={{ width: rowWidth }}>
            {game.boxes.map((box) => {
              const isPicked = game.pickedBoxId === box.id;
              return (
                <MagicBox
                  key={box.id}
                  x={box.position * slotW}
                  swapMs={cfg.swapMs}
                  absorbing={game.phase === "inserting"}
                  lidUp={lidsUp}
                  lidClosing={lidsClosing}
                  shuffling={game.phase === "shuffling"}
                  dimmed={game.pickedBoxId !== null && !isPicked}
                  opening={isPicked && game.phase === "opening"}
                  opened={isPicked && (game.phase === "emerging" || game.phase === "question" || game.phase === "feedback")}
                  clickable={boxesInteractive}
                  showPrize={isPicked}
                  lidDelayMs={box.position * 90}
                  onPick={() => game.pickBox(box.id)}
                  label={`Қуттии ${box.position + 1}`}
                />
              );
            })}
          </div>
        )}

        {}
        {game.phase === "reveal" && (
          <div className="absolute inset-0 z-40 flex items-center justify-center px-3">
            <div className="grid w-full max-w-3xl gap-2.5 sm:grid-cols-3">
              {game.roundQuestions.map((q, i) => (
                <div
                  key={i}
                  className="rounded-2xl border-2 border-amber-300/60 bg-white/95 px-3 py-3 text-center shadow-2xl"
                  style={{ animation: `game-round-in 0.4s ease-out ${i * 0.12}s backwards` }}
                >
                  <p className="text-[10px] font-black uppercase tracking-widest text-fuchsia-600">
                    Савол {String.fromCharCode(65 + i)}
                  </p>
                  <p className="mt-1.5 text-sm font-bold leading-snug text-[#3b0764]">{q.question}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {}
        {game.phase === "inserting" &&
          game.boxes.map((box) => {
            const q = game.roundQuestions[box.questionIndex];
            if (!q) return null;
            return (
              <FlyingQuestionCard
                key={box.id}
                question={q}
                mode="into"
                compact
                offsetX={offsetToSlot(box.position)}
                offsetY={CARD_TO_BOX_Y}
                centerYOffset={0}
                playKey={`${game.round}-${box.id}`}
              />
            );
          })}

        {}
        {(game.phase === "emerging" || game.phase === "question") && game.activeQuestion && (
          <FlyingQuestionCard
            question={game.activeQuestion}
            mode={game.phase === "emerging" ? "outOf" : "settled"}
            offsetX={offsetToSlot(openedBox?.position ?? 1)}
            offsetY={CARD_TO_BOX_Y - cardRestY}
            centerYOffset={cardRestY}
            playKey={game.round}
          />
        )}

        {game.phase === "emerging" && (
          <div className="pointer-events-none absolute inset-x-0 top-[18%] z-50 flex justify-center px-4">
            <span
              className="rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 px-5 py-2.5 text-base font-black text-white shadow-2xl"
              style={{ animation: "mascot-pop 0.5s ease-out" }}
            >
              Қуттӣ кушода мешавад...
            </span>
          </div>
        )}

        {}
        {game.phase === "question" && game.activeQuestion && (
          <div className="absolute inset-x-0 bottom-0 z-50 flex justify-center px-3 pb-10 sm:pb-12">
            <QuestionPanel question={game.activeQuestion} picked={game.pickedAnswer} onAnswer={game.answer} />
          </div>
        )}

        {}
        {game.phase === "feedback" && game.activeQuestion && (
          <FeedbackPanel
            correct={game.answerCorrect === true}
            question={game.activeQuestion}
            picked={game.pickedAnswer}
            isLastRound={game.round + 1 >= game.totalRounds || game.lives <= 0}
            onNext={game.next}
          />
        )}
      </div>
    </ClassroomScene>
  );
}

function CloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button
      type="button"
      onClick={onClose}
      aria-label="Пӯшидан"
      className="absolute right-3 top-3 z-50 flex h-10 w-10 items-center justify-center rounded-xl bg-black/40 text-white backdrop-blur-md transition hover:bg-black/60"
    >
      <X className="h-4 w-4" />
    </button>
  );
}


function FeedbackPanel({
  correct,
  question,
  picked,
  isLastRound,
  onNext,
}: {
  correct: boolean;
  question: ShuffleQuestion;
  picked: number | null;
  isLastRound: boolean;
  onNext: () => void;
}) {
  
  
  
  const btnRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    btnRef.current?.focus();
  }, []);

  const correctText = question.answers[question.correctAnswer];
  const pickedText = picked !== null ? question.answers[picked] : null;

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 px-4 py-6 backdrop-blur-sm">
      <div
        className="relative w-full max-w-md rounded-3xl border border-white/20 bg-white/97 p-5 text-center shadow-2xl"
        style={{ animation: "mascot-pop 0.45s ease-out" }}
      >
        {correct && <Burst playKey="mbox-correct" />}

        <p className="text-3xl">{correct ? "🎉" : "❌"}</p>
        <p className={`relative mt-2 text-xl font-black ${correct ? "text-emerald-600" : "text-red-600"}`}>
          {correct ? "Офарин! Ҷавоби дуруст! ✅" : "Ҷавоби нодуруст! ❌"}
        </p>

        {correct && <p className="relative mt-1 text-sm font-black text-amber-600">+100 хол</p>}

        {}
        {!correct && pickedText && (
          <p className="relative mt-3 rounded-xl bg-red-50 px-3 py-2 text-left text-sm font-semibold text-red-800">
            <span className="mr-1 font-black">Ҷавоби шумо:</span>
            {pickedText}
          </p>
        )}
        {!correct && (
          <p className="relative mt-2 rounded-xl bg-emerald-50 px-3 py-2 text-left text-sm font-semibold text-emerald-800">
            <span className="mr-1 font-black">Ҷавоби дуруст:</span>
            {correctText}
          </p>
        )}

        {question.explanation && (
          <div className="relative mt-3 rounded-xl bg-violet-50 px-3 py-2.5 text-left">
            <p className="text-xs font-black uppercase tracking-wide text-violet-700">Чаро ин ҷавоб дуруст аст? 💡</p>
            <p className="mt-1 text-sm font-medium leading-relaxed text-[#3b0764]">{question.explanation}</p>
          </div>
        )}

        <button
          ref={btnRef}
          type="button"
          onClick={onNext}
          className="relative mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-600 py-3.5 text-sm font-black text-white shadow-lg transition hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]"
        >
          {isLastRound ? "Натиҷа" : "Раунди нав"}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
