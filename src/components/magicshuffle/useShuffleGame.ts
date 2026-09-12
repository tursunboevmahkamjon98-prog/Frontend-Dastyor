"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BOX_COUNT,
  BoxState,
  Phase,
  STARTING_LIVES,
  STREAK_BONUS_AT,
  STREAK_BONUS_POINTS,
  ShuffleQuestion,
  TOTAL_ROUNDS,
  answerPoints,
  applySwap,
  buildRoundQuestions,
  initialBoxes,
  planShuffle,
  randomOrder,
  roundConfig,
} from "./types";
import { magicSfx } from "./sounds";

/** Everything the UI needs to render, and the actions it can take. All phase
 * sequencing, timing and scoring lives here so the components stay
 * presentational — the one exception is the swap *animation*, which the boxes
 * render off `boxes[].position` changing (this hook drives those position
 * changes on a timer; CSS does the interpolation). */
export interface ShuffleGameState {
  phase: Phase;
  round: number; // 0-based
  boxes: BoxState[];
  /** This round's three questions, in the order they're shown during the
   * "look them over" beat. Which box got which is `boxes[].questionIndex`. */
  roundQuestions: ShuffleQuestion[];
  countdownStep: number; // 3, 2, 1, 0 (=Биёед!)
  pickedBoxId: number | null;
  /** The question that was really inside the box the player opened — read
   * back out through that box's own `questionIndex`, never re-picked. */
  activeQuestion: ShuffleQuestion | null;
  pickedAnswer: number | null;
  answerCorrect: boolean | null;
  score: number;
  lives: number;
  streak: number;
  maxStreak: number;
  correctAnswers: number;
  questionsAnswered: number;
  /** How many rounds this run has — chosen by the player on the setup
   * screen (5/8/10), so it isn't a constant. Derived from how many
   * questions actually came back, three per round. */
  totalRounds: number;
  comboToast: string | null;
  elapsedSeconds: number;
}

export interface ShuffleGameApi extends ShuffleGameState {
  start: (questions: ShuffleQuestion[]) => void;
  pickBox: (boxId: number) => void;
  answer: (index: number) => void;
  next: () => void;
  backToSetup: () => void;
}

const COUNTDOWN_STEP_MS = 620;
/** Lids rising before the questions are posted in. */
const LIDS_OPEN_MS = 900;
/** The three cards flying into their boxes. */
const INSERT_MS = 1500;
/** Lids coming back down, plus the "Қуттиҳо баста шуданд!" beat. */
const LIDS_CLOSE_MS = 1100;
/** Box shake → lid lift → light. */
const OPENING_MS = 950;
/** Card flies back out of the box to the centre of the screen. */
const EMERGE_MS = 950;

/** Streak at which the "Комбо xN!" toast starts appearing — below this a
 * toast on every single answer would just be noise. */
const COMBO_TOAST_FROM = 3;

export function useShuffleGame(): ShuffleGameApi {
  const [phase, setPhase] = useState<Phase>("setup");
  const [round, setRound] = useState(0);
  const [boxes, setBoxes] = useState<BoxState[]>(() => initialBoxes([0, 1, 2]));
  const [roundQuestions, setRoundQuestions] = useState<ShuffleQuestion[]>([]);
  const [countdownStep, setCountdownStep] = useState(3);
  const [pickedBoxId, setPickedBoxId] = useState<number | null>(null);
  const [pickedAnswer, setPickedAnswer] = useState<number | null>(null);
  const [answerCorrect, setAnswerCorrect] = useState<boolean | null>(null);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(STARTING_LIVES);
  const [streak, setStreak] = useState(0);
  const [maxStreak, setMaxStreak] = useState(0);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [totalRounds, setTotalRounds] = useState(TOTAL_ROUNDS);
  const [comboToast, setComboToast] = useState<string | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  /** The whole run's question supply — enough for BOX_COUNT per round, so a
   * ref rather than state: it's read inside timer callbacks and never needs
   * to trigger a re-render on its own. */
  const pool = useRef<ShuffleQuestion[]>([]);

  // Every pending timeout is tracked here and cleared on unmount — this game
  // chains a lot of them (reveal → lids → insert → close → countdown → N
  // swaps → open → emerge), and a pupil closing the overlay mid-chain must
  // not leave one running that then calls setState on an unmounted tree.
  //
  // A Set, and each timer removes its own id as it fires, so the collection
  // stays the size of what's actually PENDING rather than growing by one for
  // every beat of every round across a whole run.
  const timers = useRef<Set<number>>(new Set());
  const runStartedAt = useRef<number>(0);

  const clearTimers = useCallback(() => {
    timers.current.forEach((id) => window.clearTimeout(id));
    timers.current.clear();
  }, []);

  const later = useCallback((fn: () => void, ms: number) => {
    const id = window.setTimeout(() => {
      timers.current.delete(id);
      fn();
    }, ms);
    timers.current.add(id);
    return id;
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  // Wall-clock for the result screen. Runs only while a run is actually in
  // progress, so time spent on the setup/result screens isn't counted
  // against the player.
  useEffect(() => {
    if (phase === "setup" || phase === "result") return;
    const id = window.setInterval(() => {
      setElapsedSeconds(Math.round((Date.now() - runStartedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  /** One round, from the top:
   *  1. show all three questions,
   *  2. lids rise on all three boxes at once,
   *  3. the three cards fly in, one per box,
   *  4. lids close — from here nothing on screen distinguishes the boxes,
   *  5. countdown, then the real shuffle,
   *  6. the player picks.
   *
   * Which box holds which question is decided HERE, before anything moves,
   * as `questionIndex` on each box — a box *id* mapping, never a position
   * one. Nothing after this point reassigns it, so opening a box genuinely
   * returns the question that went into it. */
  const beginRound = useCallback(
    (roundIndex: number) => {
      // Defensive: a new round always starts from a clean slate, so a beat
      // left over from the previous round's chain can never fire partway
      // into this one and desync the phase from the boxes on screen.
      clearTimers();
      const cfg = roundConfig(roundIndex);

      // Three questions for this round, and a random box→question mapping
      // so box 0 isn't always holding the first one.
      const slice = pool.current.slice(roundIndex * BOX_COUNT, roundIndex * BOX_COUNT + BOX_COUNT);
      setRoundQuestions(slice);
      let working = initialBoxes(randomOrder(BOX_COUNT));

      setBoxes(working);
      setPickedBoxId(null);
      setPickedAnswer(null);
      setAnswerCorrect(null);
      setPhase("reveal");
      magicSfx.wand();

      // 1. All three questions on screen together.
      later(() => {
        // 2. Every lid rises at once.
        setPhase("lidsOpen");
        magicSfx.lidOpen();

        later(() => {
          // 3. The three cards fly in, one into each box.
          setPhase("inserting");
          magicSfx.wand();

          later(() => {
            // 4. Lids close. After this the boxes are indistinguishable.
            setPhase("lidsClose");
            magicSfx.lidClose();

            later(() => {
              // 5. Countdown, then the shuffle.
              setPhase("countdown");
              setCountdownStep(3);
              magicSfx.countdown();

              [2, 1].forEach((n, i) => {
                later(() => {
                  setCountdownStep(n);
                  magicSfx.countdown();
                }, COUNTDOWN_STEP_MS * (i + 1));
              });

              later(() => {
                setCountdownStep(0);
                setPhase("shuffling");
                const plan = planShuffle(cfg.swaps);
                plan.forEach((step, i) => {
                  later(() => {
                    working = applySwap(working, step);
                    setBoxes(working);
                    magicSfx.swoosh();
                  }, cfg.swapMs * i);
                });
                // Once the last swap's animation has finished, hand control
                // to the player. `+ 140` is a small settle beat so the boxes
                // are visibly at rest before they become clickable.
                later(() => {
                  setPhase("choosing");
                  magicSfx.ready();
                }, cfg.swapMs * plan.length + 140);
              }, COUNTDOWN_STEP_MS * 3);
            }, LIDS_CLOSE_MS);
          }, INSERT_MS);
        }, LIDS_OPEN_MS);
      }, cfg.revealMs);
    },
    [clearTimers, later]
  );

  const start = useCallback(
    (questions: ShuffleQuestion[]) => {
      clearTimers();
      // Each round consumes BOX_COUNT questions (one per box), so the run is
      // as long as the generated set allows. Padded up to a whole number of
      // rounds in case the model returned a couple fewer than asked for.
      const rounds = Math.max(1, Math.floor(questions.length / BOX_COUNT));
      pool.current = buildRoundQuestions(questions, rounds * BOX_COUNT);
      setTotalRounds(rounds);
      runStartedAt.current = Date.now();
      setRound(0);
      setScore(0);
      setLives(STARTING_LIVES);
      setStreak(0);
      setMaxStreak(0);
      setCorrectAnswers(0);
      setQuestionsAnswered(0);
      setComboToast(null);
      setElapsedSeconds(0);
      magicSfx.click();
      beginRound(0);
    },
    [beginRound, clearTimers]
  );

  const pickBox = useCallback(
    (boxId: number) => {
      if (phase !== "choosing") return;
      setPickedBoxId(boxId);
      setPhase("opening");
      magicSfx.lidOpen();

      later(() => {
        // Whatever was really in this box now flies out. There's no
        // right-or-wrong box any more — every box held a real question —
        // so this always leads to the question, never to an empty reveal.
        setPhase("emerging");
        magicSfx.reward();
        later(() => setPhase("question"), EMERGE_MS);
      }, OPENING_MS);
    },
    [later, phase]
  );

  const openedBox = boxes.find((b) => b.id === pickedBoxId) ?? null;
  const activeQuestion = openedBox ? (roundQuestions[openedBox.questionIndex] ?? null) : null;

  const answer = useCallback(
    (index: number) => {
      if (phase !== "question" || pickedAnswer !== null) return;
      if (!activeQuestion) return;
      const correct = index === activeQuestion.correctAnswer;
      setPickedAnswer(index);
      setAnswerCorrect(correct);
      setQuestionsAnswered((n) => n + 1);

      if (correct) {
        const newStreak = streak + 1;
        let gained = answerPoints(newStreak);
        if (newStreak === STREAK_BONUS_AT) gained += STREAK_BONUS_POINTS;
        setScore((s) => s + gained);
        setStreak(newStreak);
        setMaxStreak((m) => Math.max(m, newStreak));
        setCorrectAnswers((c) => c + 1);
        setComboToast(
          newStreak === STREAK_BONUS_AT
            ? `Супер! Бонус +${STREAK_BONUS_POINTS}`
            : newStreak >= COMBO_TOAST_FROM
              ? `Комбо x${newStreak}!`
              : null
        );
        magicSfx.correct();
      } else {
        setStreak(0);
        setLives((l) => l - 1);
        setComboToast(null);
        magicSfx.wrong();
      }
      later(() => setPhase("feedback"), 650);
    },
    [activeQuestion, later, phase, pickedAnswer, streak]
  );

  /** Advances past the feedback panel — either to the next round or, if the
   * run is over (all rounds played, or no lives left), to the result. */
  const next = useCallback(() => {
    setComboToast(null);
    // `lives` is read here rather than inside a setState updater because the
    // life change already committed during answer() — by the time the player
    // taps "next" this render's value is current.
    if (lives <= 0 || round + 1 >= totalRounds) {
      setPhase("result");
      magicSfx.victory();
      return;
    }
    const nextRound = round + 1;
    setRound(nextRound);
    beginRound(nextRound);
  }, [beginRound, lives, round, totalRounds]);

  const backToSetup = useCallback(() => {
    clearTimers();
    setPhase("setup");
  }, [clearTimers]);

  return {
    phase,
    round,
    boxes,
    roundQuestions,
    countdownStep,
    pickedBoxId,
    activeQuestion,
    pickedAnswer,
    answerCorrect,
    score,
    lives,
    streak,
    maxStreak,
    correctAnswers,
    questionsAnswered,
    totalRounds,
    comboToast,
    elapsedSeconds,
    start,
    pickBox,
    answer,
    next,
    backToSetup,
  };
}
