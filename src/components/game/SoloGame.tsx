"use client";

import { useEffect, useRef, useState } from "react";
import { Heart, Flame, Star, GripVertical, Send } from "lucide-react";
import { Round, Difficulty, DIFFICULTY_CONFIG, BASE_TIME_SECONDS, SoloResult, P1_KEYS, GameTemplate } from "./types";
import { Burst } from "./effects";
import { SoloProgress, TemplateScene } from "./templates";
import { sfx } from "./sound";

const LEVEL_SIZE = 3; // rounds per difficulty tier — see the file doc below

// A small "what kind of round is this" badge shown above every card — pure
// flavor (no gameplay effect), but a bare white card with no framing reads
// as a form, not a game; naming the round type with an icon is a cheap way
// to make each one feel like its own little event.
// Kahoot-style per-letter tile colors for multiple-choice options — always
// on (not just on hover/select), same as the reference: the button's own
// border/background still carries the correct/wrong signal once revealed
// (see the quiz option button below), this badge is pure identity, not
// feedback, so keeping it colored throughout doesn't compete with that.
const OPTION_COLORS = ["bg-[#7c3aed]", "bg-[#16a34a]", "bg-[#2563eb]", "bg-[#ea580c]"];

const ROUND_META: Record<Round["type"], { emoji: string; label: string }> = {
  quiz: { emoji: "🎯", label: "Викторина" },
  true_false: { emoji: "⚖️", label: "Верно или неверно" },
  matching: { emoji: "🔗", label: "Сопоставление" },
  order: { emoji: "🔢", label: "Порядок" },
  speed: { emoji: "⚡", label: "На скорость" },
};


/** Solo campaign — one child plays against the clock/streak rather than a
 * simulated opponent (product decision: a fake "AI" answering alongside a
 * quiz format would just be theater, since there's nothing for it to
 * actually compete on). Difficulty is chosen once on the start screen
 * (lives/time budget/score multiplier, see DIFFICULTY_CONFIG) and then
 * ramps further every LEVEL_SIZE rounds within the run — shrinking the
 * answer window and raising the score multiplier — so the game gets
 * harder both by upfront choice and by simply playing longer.
 *
 * SoloGame owns only what survives across rounds (lives/score/streak/
 * badges). Everything scoped to a single round — the countdown, the
 * correct/wrong flash, the answer widget itself — lives in Stage below,
 * which is remounted fresh every round via `key={index}`; that remount IS
 * the reset, so there's no effect anywhere resyncing local state to a
 * prop change. */
export default function SoloGame({
  rounds,
  difficulty,
  template,
  onFinish,
}: {
  rounds: Round[];
  difficulty: Difficulty;
  template: GameTemplate;
  onFinish: (result: SoloResult) => void;
}) {
  const diff = DIFFICULTY_CONFIG[difficulty];
  const [index, setIndex] = useState(0);
  const [lives, setLives] = useState(diff.lives);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [maxStreak, setMaxStreak] = useState(0);
  const [speedBonusCount, setSpeedBonusCount] = useState(0);
  const [mistakeCount, setMistakeCount] = useState(0);
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const announcedLevel = useRef(1);

  const round = rounds[index];
  const level = Math.floor(index / LEVEL_SIZE) + 1;
  const levelTimeFactor = Math.max(0.55, 1 - (level - 1) * 0.08);
  const timeBudget = Math.round(BASE_TIME_SECONDS[round.type] * diff.timeMultiplier * levelTimeFactor);

  // Play the level-up chime exactly once per new tier — a ref-guarded
  // effect with no setState in it (just an external side effect, which is
  // what effects are for); the toast's own visibility/timing below is
  // handled by CSS off the `level` value directly, with no extra state.
  useEffect(() => {
    if (announcedLevel.current !== level) {
      announcedLevel.current = level;
      if (level > 1) sfx.levelUp();
    }
  }, [level]);

  useEffect(() => () => {
    if (advanceTimer.current) clearTimeout(advanceTimer.current);
  }, []);

  function handleResolved(correct: boolean, bonus: boolean) {
    const remainingLives = correct ? lives : lives - 1;
    // Computed explicitly here (not read back out of state inside finish())
    // because finish() only runs 1000ms later via setTimeout, by which
    // point React has already re-rendered with the setState calls below
    // applied — a finish() that instead closed over score/mistakeCount/
    // maxStreak as outer-scope state would silently use this render's
    // stale pre-update values, undercounting exactly the round that just
    // triggered it (the one case that matters most: the final round).
    let finalScore = score;
    let finalMaxStreak = maxStreak;
    let finalMistakeCount = mistakeCount;
    let finalSpeedBonusCount = speedBonusCount;

    if (correct) {
      const newStreak = streak + 1;
      const levelMult = 1 + (level - 1) * 0.15;
      const streakMult = 1 + Math.floor(newStreak / 3) * 0.5;
      const points = Math.round(100 * diff.scoreMultiplier * levelMult * streakMult) + (bonus ? 50 : 0);
      finalScore = score + points;
      finalMaxStreak = Math.max(maxStreak, newStreak);
      if (bonus) finalSpeedBonusCount = speedBonusCount + 1;
      setScore(finalScore);
      setStreak(newStreak);
      setMaxStreak(finalMaxStreak);
      if (bonus) setSpeedBonusCount(finalSpeedBonusCount);
    } else {
      finalMistakeCount = mistakeCount + 1;
      setStreak(0);
      setMistakeCount(finalMistakeCount);
      setLives(remainingLives);
    }

    if (remainingLives <= 0) {
      advanceTimer.current = setTimeout(
        () => finish(false, index, remainingLives, finalScore, finalMaxStreak, finalMistakeCount, finalSpeedBonusCount),
        1000
      );
      return;
    }
    advanceTimer.current = setTimeout(() => {
      if (index + 1 >= rounds.length) {
        finish(true, rounds.length, remainingLives, finalScore, finalMaxStreak, finalMistakeCount, finalSpeedBonusCount);
      } else {
        setIndex((i) => i + 1);
      }
    }, 1000);
  }

  function finish(
    won: boolean,
    roundsCleared: number,
    finalLives: number,
    finalScore: number,
    finalMaxStreak: number,
    finalMistakeCount: number,
    finalSpeedBonusCount: number
  ) {
    const badges: string[] = [];
    if (finalMistakeCount === 0) badges.push("perfect");
    if (finalMaxStreak >= 5) badges.push("streak");
    if (finalSpeedBonusCount >= 3) badges.push("speedster");
    if (won && finalLives === 1) badges.push("survivor");
    onFinish({ mode: "solo", won, score: finalScore, level, maxStreak: finalMaxStreak, roundsCleared, totalRounds: rounds.length, badges });
  }

  return (
    <TemplateScene template={template}>
    {/* min-h-0 + the scrollable stage below: this container is exactly
        the viewport height, and a long question with four long options
        does not fit what is left after the HUD, the progress bar and the
        round line on a 360x640 phone. Without a scroll the last option
        is simply unreachable — the player can see three answers to a
        four-answer question. */}
    <div className="flex h-full w-full min-h-0 flex-col px-3 pb-4 pt-3 sm:px-8 sm:pb-6 sm:pt-4">
      {/* HUD */}
      <div className="mx-auto flex w-full max-w-md items-center justify-between text-white">
        <div className="flex items-center gap-1">
          {Array.from({ length: diff.lives }, (_, i) => (
            <Heart key={i} className={`h-5 w-5 ${i < lives ? "fill-red-400 text-red-400" : "text-white/20"}`} />
          ))}
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-bold">
          <Star className="h-3.5 w-3.5 text-amber-300" />
          <span key={score} style={{ animation: "game-pop 0.3s ease-out" }}>
            {score}
          </span>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-bold">
          <Flame
            className={`h-3.5 w-3.5 ${streak >= 3 ? "text-orange-400" : "text-white/50"}`}
            style={{ animation: streak >= 3 ? "game-flame-glow 0.8s ease-in-out infinite" : undefined }}
          />
          <span key={streak} style={{ animation: streak > 0 ? "game-pop 0.3s ease-out" : undefined }}>
            {streak}
          </span>
        </div>
      </div>

      <div className="mx-auto mt-3 w-full max-w-md">
        <SoloProgress template={template} pct={(index + 1) / rounds.length} />
      </div>

      <div className="relative mx-auto mt-2 flex w-full max-w-md items-center justify-between text-[11px] font-medium text-white/50">
        <span>
          Раунд {index + 1} / {rounds.length}
        </span>
        <span>Уровень {level}</span>
      </div>

      {/* Keyed by `level` rather than toggled by state: remounting on every
          new tier replays the animation from scratch, and the keyframe
          itself (game-levelup-toast, globals.css) holds then fades to
          opacity 0 and stays there — invisible and non-interactive
          (pointer-events-none) for the rest of the run, no timer needed to
          unmount it. */}
      {level > 1 && (
        <div
          key={level}
          className="pointer-events-none absolute left-1/2 top-1/3 z-10 rounded-2xl bg-white px-6 py-3 text-center shadow-2xl"
          style={{ animation: "game-levelup-toast 1.6s ease-out forwards" }}
        >
          <p className="text-lg font-extrabold text-[#6d28d9]">Уровень {level}!</p>
          <p className="text-xs text-[#7c3aed]">Держись — стало сложнее ⚡</p>
        </div>
      )}

      {/* Stage — key={index} is the reset: a fresh Stage instance per round
          means no effect has to resync timeLeft/feedback to the new round. */}
      <div className="relative mx-auto mt-4 w-full min-h-0 max-w-md flex-1 overflow-y-auto sm:mt-6">
        <Stage key={index} round={round} timeBudget={timeBudget} onResolve={handleResolved} />
      </div>
    </div>
    </TemplateScene>
  );
}


function TimerRing({ timeLeft, timeBudget, hard }: { timeLeft: number; timeBudget: number; hard: boolean }) {
  const pct = Math.max(0, timeLeft / timeBudget);
  const urgent = hard && timeLeft <= 3;
  return (
    <div className="mx-auto flex justify-center">
      <div className={`relative flex h-12 w-12 items-center justify-center ${urgent ? "text-red-300" : "text-white"}`}>
        <svg viewBox="0 0 48 48" className="absolute inset-0 -rotate-90">
          <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="4" />
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 20}
            strokeDashoffset={2 * Math.PI * 20 * (1 - pct)}
            style={{ transition: "stroke-dashoffset 1s linear" }}
          />
        </svg>
        <span className="text-sm font-extrabold">{Math.max(0, timeLeft)}</span>
      </div>
    </div>
  );
}

// One round's whole lifecycle: countdown, the answer widget for whichever
// round.type this is, the correct/wrong flash, and the little celebration
// burst — all local, because a fresh Stage exists for exactly one round
// (see key={index} above) and disappears with it.
function Stage({
  round,
  timeBudget,
  onResolve,
}: {
  round: Round;
  timeBudget: number;
  onResolve: (correct: boolean, bonus: boolean) => void;
}) {
  const [timeLeft, setTimeLeft] = useState(timeBudget);
  const [feedback, setFeedback] = useState<"correct" | "wrong" | null>(null);
  const [picked, setPicked] = useState<number | boolean | null>(null);
  const resolvedRef = useRef(false);
  // Lazy useState initializer, not useMemo: Stage mounts exactly once per
  // round, so this is a one-time "when did this round start" timestamp —
  // exactly what a lazy initializer is for, and unlike useMemo it isn't
  // flagged as an impure render call since it only ever runs once.
  const [startedAt] = useState(() => Date.now());

  function settle(correct: boolean, bonus: boolean) {
    if (resolvedRef.current) return;
    resolvedRef.current = true;
    setFeedback(correct ? "correct" : "wrong");
    if (correct) sfx.correct();
    else sfx.wrong();
    onResolve(correct, bonus);
  }

  function answer(correct: boolean, chosen: number | boolean) {
    if (picked !== null || resolvedRef.current) return;
    setPicked(chosen);
    const elapsed = (Date.now() - startedAt) / 1000;
    settle(correct, correct && elapsed < BASE_TIME_SECONDS[round.type] * 0.4);
  }

  // Countdown — quiz/true_false auto-fail at 0; matching/order/speed just
  // lose eligibility for the speed bonus, they're never forced to answer.
  useEffect(() => {
    if (feedback) return;
    if (timeLeft <= 0) {
      if (round.type === "quiz" || round.type === "true_false") settle(false, false);
      return;
    }
    const t = setTimeout(() => setTimeLeft((s) => s - 1), 1000);
    if (timeLeft <= 3) sfx.tick();
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft, feedback]);

  // Keyboard is a first-class input here too, not just touch/click — Q/W/E/R
  // pick quiz options 1-4 (Q/W double as Верно/Неверно for true_false), same
  // P1 keymap DuelGame.tsx uses, so a keyboard-playing kid gets the same
  // muscle memory in either mode.
  useEffect(() => {
    if (round.type !== "quiz" && round.type !== "true_false") return;
    function onKey(e: KeyboardEvent) {
      const idx = P1_KEYS.indexOf(e.key.toLowerCase());
      if (idx === -1) return;
      if (round.type === "quiz" && idx < round.options.length) answer(idx === round.correct_index, idx);
      if (round.type === "true_false" && idx < 2) {
        const val = idx === 0;
        answer(val === round.answer, val);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [picked]);

  const hardTimer = round.type === "quiz" || round.type === "true_false";
  const urgent = hardTimer && !feedback && timeLeft <= 3;
  // Cards for the two "real deadline" round types get a heartbeat pulse in
  // the last 3 seconds — everything else (matching/order/speed) has no
  // forced fail on timeout, so pulsing them would just be a false alarm.
  const urgentStyle = urgent ? { animation: "game-urgent-pulse 0.6s ease-in-out infinite" } : undefined;

  return (
    <>
      <TimerRing timeLeft={timeLeft} timeBudget={timeBudget} hard={hardTimer} />
      <div className="mt-3" style={{ animation: "game-round-in 0.3s ease-out" }}>
        <div className="mb-2.5 flex justify-center">
          <span className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-white/70">
            {ROUND_META[round.type].emoji} {ROUND_META[round.type].label}
          </span>
        </div>
        {round.type === "quiz" && (
          <div
            style={urgentStyle}
            className={`rounded-3xl bg-white/95 p-5 shadow-xl ${feedback === "wrong" ? "animate-[game-shake_0.4s_ease-in-out]" : ""}`}
          >
            <p className="mb-4 text-center font-bold text-[#3b0764]">{round.question}</p>
            <div className="space-y-2.5">
              {round.options.map((opt, j) => {
                const isPicked = picked === j;
                const isCorrect = j === round.correct_index;
                const revealed = picked !== null;
                return (
                  <button
                    key={j}
                    disabled={revealed}
                    onClick={() => answer(j === round.correct_index, j)}
                    className={`flex w-full items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left text-sm font-semibold transition ${
                      revealed && isCorrect
                        ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                        : revealed && isPicked
                          ? "border-red-400 bg-red-50 text-red-700"
                          : "border-violet-100 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                    }`}
                  >
                    <span
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white shadow-sm ${OPTION_COLORS[j % OPTION_COLORS.length]}`}
                    >
                      {String.fromCharCode(65 + j)}
                    </span>
                    {opt}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {round.type === "true_false" && (
          <div
            style={urgentStyle}
            className={`rounded-3xl bg-white/95 p-5 shadow-xl ${feedback === "wrong" ? "animate-[game-shake_0.4s_ease-in-out]" : ""}`}
          >
            <p className="mb-5 text-center font-bold text-[#3b0764]">{round.statement}</p>
            <div className="flex gap-3">
              {[true, false].map((val) => {
                const isPicked = picked === val;
                const revealed = picked !== null;
                const isCorrect = val === round.answer;
                return (
                  <button
                    key={String(val)}
                    disabled={revealed}
                    onClick={() => answer(val === round.answer, val)}
                    className={`flex-1 rounded-2xl border-2 py-3.5 text-sm font-bold transition ${
                      revealed && isCorrect
                        ? "border-emerald-400 bg-emerald-50 text-emerald-700"
                        : revealed && isPicked
                          ? "border-red-400 bg-red-50 text-red-700"
                          : "border-violet-100 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                    }`}
                  >
                    {val ? "✓ Верно" : "✕ Неверно"}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {round.type === "matching" && <MatchingStage round={round} onResolve={settle} startedAt={startedAt} />}
        {round.type === "order" && <OrderStage round={round} onResolve={settle} startedAt={startedAt} />}
        {round.type === "speed" && <SpeedStage round={round} onResolve={settle} timeLeft={timeLeft} />}
      </div>
      {feedback === "correct" && <Burst playKey={round.type} />}
    </>
  );
}

// A matched pair's connector: a real drawn line between the two boxes
// (per the reference product's "клик слева, клик справа, соединить их
// линией" spec), not just two boxes independently turning green. Position
// is computed from the two buttons' own bounding rects the instant a match
// lands, relative to the shared container — no layout library, just
// getBoundingClientRect and a bit of arithmetic.
interface MatchLine {
  key: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

function MatchingStage({
  round,
  onResolve,
  startedAt,
}: {
  round: Extract<Round, { type: "matching" }>;
  onResolve: (correct: boolean, bonus: boolean) => void;
  startedAt: number;
}) {
  const [rightShuffled] = useState(() => [...round.pairs.map((p) => p.right)].sort(() => Math.random() - 0.5));
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [matched, setMatched] = useState<Record<number, string>>({});
  const [wrongPair, setWrongPair] = useState<{ left: number; right: string } | null>(null);
  const [lines, setLines] = useState<MatchLine[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const leftRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const rightRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const wonRef = useRef(false);
  const done = Object.keys(matched).length === round.pairs.length;

  useEffect(() => {
    if (done && !wonRef.current) {
      wonRef.current = true;
      const elapsed = (Date.now() - startedAt) / 1000;
      onResolve(true, elapsed < BASE_TIME_SECONDS.matching * 0.6);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);

  function drawLine(leftIndex: number, right: string) {
    const container = containerRef.current;
    const leftEl = leftRefs.current[leftIndex];
    const rightEl = rightRefs.current[right];
    if (!container || !leftEl || !rightEl) return;
    const c = container.getBoundingClientRect();
    const l = leftEl.getBoundingClientRect();
    const r = rightEl.getBoundingClientRect();
    setLines((prev) => [
      ...prev,
      { key: leftIndex, x1: l.right - c.left, y1: l.top + l.height / 2 - c.top, x2: r.left - c.left, y2: r.top + r.height / 2 - c.top },
    ]);
  }

  function pickRight(right: string) {
    if (selectedLeft === null || done) return;
    const leftIndex = selectedLeft;
    if (round.pairs[leftIndex].right === right) {
      setMatched((m) => ({ ...m, [leftIndex]: right }));
      drawLine(leftIndex, right);
      sfx.correct();
    } else {
      setWrongPair({ left: leftIndex, right });
      sfx.wrong();
      setTimeout(() => setWrongPair(null), 400);
    }
    setSelectedLeft(null);
  }

  return (
    <div ref={containerRef} className="relative rounded-3xl bg-white/95 p-5 shadow-xl">
      {round.instructions && <p className="mb-3 text-center text-xs text-[#6d28d9]">{round.instructions}</p>}
      {/* Connector lines live in their own SVG layer above the boxes but
          below their text (pointer-events-none so clicks pass through). */}
      <svg className="pointer-events-none absolute inset-0 h-full w-full">
        {lines.map((l) => (
          <line
            key={l.key}
            x1={l.x1}
            y1={l.y1}
            x2={l.x2}
            y2={l.y2}
            stroke="#10b981"
            strokeWidth={3}
            strokeLinecap="round"
            pathLength={1}
            style={{ strokeDasharray: 1, strokeDashoffset: 1, animation: "game-line-draw 0.35s ease-out forwards" }}
          />
        ))}
      </svg>
      <div className="relative grid grid-cols-2 gap-3">
        <div className="space-y-2">
          {round.pairs.map((p, i) => (
            <button
              key={i}
              ref={(el) => {
                leftRefs.current[i] = el;
              }}
              disabled={matched[i] !== undefined}
              onClick={() => setSelectedLeft(i)}
              className={`w-full rounded-xl border-2 px-3 py-2 text-left text-sm font-medium transition ${
                matched[i] !== undefined
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : selectedLeft === i
                    ? "border-[#7c3aed] bg-violet-100 text-[#4c1d95]"
                    : wrongPair?.left === i
                      ? "animate-[game-shake_0.4s_ease-in-out] border-red-300 bg-red-50 text-red-700"
                      : "border-violet-100 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
              }`}
            >
              {p.left}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {rightShuffled.map((right, i) => {
            const isUsed = Object.values(matched).includes(right);
            return (
              <button
                key={i}
                ref={(el) => {
                  rightRefs.current[right] = el;
                }}
                disabled={isUsed}
                onClick={() => pickRight(right)}
                className={`w-full rounded-xl border-2 px-3 py-2 text-left text-sm font-medium transition ${
                  isUsed
                    ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                    : wrongPair?.right === right
                      ? "animate-[game-shake_0.4s_ease-in-out] border-red-300 bg-red-50 text-red-700"
                      : "border-violet-100 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                }`}
              >
                {right}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// Shuffles, but never leaves the deck in the already-correct order — a
// real risk with only 3-5 items, and it would make the round trivially
// "solved" before the pupil dragged anything.
function shuffleNotSolved<T>(items: T[]): T[] {
  const s = [...items].sort(() => Math.random() - 0.5);
  if (items.length > 1 && s.every((it, i) => it === items[i])) {
    [s[0], s[1]] = [s[1], s[0]];
  }
  return s;
}

function OrderStage({
  round,
  onResolve,
  startedAt,
}: {
  round: Extract<Round, { type: "order" }>;
  onResolve: (correct: boolean, bonus: boolean) => void;
  startedAt: number;
}) {
  const [items, setItems] = useState(() => shuffleNotSolved(round.items));
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [dragOffset, setDragOffset] = useState(0);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const dragRef = useRef<{ index: number; startY: number } | null>(null);
  const wonRef = useRef(false);
  const correct = items.every((it, i) => it === round.items[i]);

  useEffect(() => {
    if (correct && !wonRef.current) {
      wonRef.current = true;
      sfx.correct();
      const elapsed = (Date.now() - startedAt) / 1000;
      onResolve(true, elapsed < BASE_TIME_SECONDS.order * 0.6);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [correct]);

  // Pointer Events (not native HTML5 drag-and-drop, which touch browsers
  // don't fire at all) so the same handful of handlers drags with mouse,
  // touch, or pen alike — this app is mobile-first, and a "reorder by
  // dragging" round that only worked with a mouse would be a regression
  // from the old tap-in-sequence version, not an upgrade.
  function onPointerDown(e: React.PointerEvent, index: number) {
    if (correct) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    dragRef.current = { index, startY: e.clientY };
    setDraggingIndex(index);
    setDragOffset(0);
  }

  function onPointerMove(e: React.PointerEvent) {
    const drag = dragRef.current;
    if (!drag) return;
    setDragOffset(e.clientY - drag.startY);
    for (let i = 0; i < rowRefs.current.length; i++) {
      if (i === drag.index) continue;
      const row = rowRefs.current[i];
      if (!row) continue;
      const rect = row.getBoundingClientRect();
      const mid = rect.top + rect.height / 2;
      const movingDown = i > drag.index && e.clientY > mid;
      const movingUp = i < drag.index && e.clientY < mid;
      if (movingDown || movingUp) {
        // Capture the OLD index before mutating drag.index below — setItems'
        // updater runs on React's schedule, not synchronously right here,
        // so by the time it actually executes it would otherwise see
        // drag.index already mutated to the NEW value and splice/re-insert
        // the same item at the same spot (a silent no-op reorder).
        const fromIndex = drag.index;
        setItems((prev) => {
          const next = [...prev];
          const [moved] = next.splice(fromIndex, 1);
          next.splice(i, 0, moved);
          return next;
        });
        drag.index = i;
        drag.startY = e.clientY;
        setDraggingIndex(i);
        break;
      }
    }
  }

  function onPointerUp() {
    dragRef.current = null;
    setDraggingIndex(null);
    setDragOffset(0);
  }

  return (
    <div className={`rounded-3xl bg-white/95 p-5 shadow-xl ${correct ? "animate-[game-order-win_0.4s_ease-out]" : ""}`}>
      {round.instructions && <p className="mb-3 text-center text-xs text-[#6d28d9]">{round.instructions}</p>}
      <div className="space-y-2">
        {items.map((item, i) => (
          <div
            key={item}
            ref={(el) => {
              rowRefs.current[i] = el;
            }}
            onPointerDown={(e) => onPointerDown(e, i)}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            style={{
              touchAction: "none",
              transform: draggingIndex === i ? `translateY(${dragOffset}px) scale(1.02)` : undefined,
              zIndex: draggingIndex === i ? 10 : undefined,
              transition: draggingIndex === i ? "none" : "transform 0.15s ease-out",
            }}
            className={`relative flex cursor-grab items-center gap-2.5 rounded-xl border-2 px-3 py-2.5 text-sm font-medium select-none active:cursor-grabbing ${
              correct ? "border-emerald-400 bg-emerald-50 text-emerald-700" : "border-violet-100 bg-violet-50/60 text-[#3b0764]"
            }`}
          >
            <GripVertical className="h-4 w-4 shrink-0 text-violet-300" />
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white text-[10px] font-bold text-[#7c3aed] shadow-sm">
              {i + 1}
            </span>
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

// Loose-enough equality for a typed short-answer: trims/lowercases/drops
// punctuation, and accepts a typed answer that's a close-enough substring
// of the expected one (catches "3" vs "3." or a missing trailing word)
// without accepting an empty or wildly short guess.
function normalizeAnswer(s: string): string {
  return s.trim().toLowerCase().replace(/[.,!?;:"'«»`]/g, "");
}
function answersMatch(typed: string, expected: string): boolean {
  const a = normalizeAnswer(typed);
  const b = normalizeAnswer(expected);
  if (!a) return false;
  if (a === b) return true;
  return b.length > 0 && b.includes(a) && a.length >= Math.max(2, Math.floor(b.length * 0.6));
}

// A real typed answer under a countdown (per the reference product's
// "тренажер на скорость": keyboard input, timer, +1/-1 scoring) — replaces
// the old single reveal-button, which asked nothing of the pupil beyond a
// tap. Shares Stage's own countdown (`timeLeft` prop) rather than running
// a second one, so time running out here auto-submits whatever's typed
// instead of hanging the round forever waiting for a submit that never
// comes.
function SpeedStage({
  round,
  onResolve,
  timeLeft,
}: {
  round: Extract<Round, { type: "speed" }>;
  onResolve: (correct: boolean, bonus: boolean) => void;
  timeLeft: number;
}) {
  const [value, setValue] = useState("");
  const [result, setResult] = useState<"correct" | "wrong" | null>(null);
  const resolvedRef = useRef(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [startedAt] = useState(() => Date.now());

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function submit() {
    if (resolvedRef.current) return;
    const ok = answersMatch(value, round.answer);
    resolvedRef.current = true;
    setResult(ok ? "correct" : "wrong");
    if (ok) sfx.correct();
    else sfx.wrong();
    const elapsed = (Date.now() - startedAt) / 1000;
    onResolve(ok, ok && elapsed < (round.time_limit_seconds ?? BASE_TIME_SECONDS.speed) * 0.4);
  }

  // Auto-submits whatever's typed (even blank) once Stage's shared timer
  // runs out — a speed round has to end somehow if the pupil never hits
  // enter/the button.
  useEffect(() => {
    if (timeLeft <= 0 && !resolvedRef.current) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  return (
    <div className={`rounded-3xl bg-white/95 p-5 shadow-xl ${result === "wrong" ? "animate-[game-shake_0.4s_ease-in-out]" : ""}`}>
      <p className="mb-4 text-center font-bold text-[#3b0764]">{round.question}</p>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          disabled={result !== null}
          placeholder="Твой ответ…"
          className={`flex-1 rounded-xl border-2 px-3.5 py-2.5 text-sm font-medium outline-none transition ${
            result === "correct"
              ? "border-emerald-400 bg-emerald-50 text-emerald-700"
              : result === "wrong"
                ? "border-red-400 bg-red-50 text-red-700"
                : "border-violet-200 bg-violet-50/60 text-[#3b0764] focus:border-[#7c3aed]"
          }`}
        />
        <button
          onClick={submit}
          disabled={result !== null || !value.trim()}
          className="flex shrink-0 items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#7c3aed] to-[#c026d3] px-4 py-2.5 text-sm font-bold text-white shadow-md disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      {result === "wrong" && (
        <p className="mt-3 rounded-xl bg-violet-50 p-3 text-center text-sm font-semibold text-[#4c1d95]">Ответ: {round.answer}</p>
      )}
    </div>
  );
}
