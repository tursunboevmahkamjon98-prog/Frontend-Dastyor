"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LabQuestion, Phase, STARTING_LIVES, scoreFor } from "./types";
import { labSfx } from "./sounds";

/** A floating "+50 ⭐" award, spawned on a correct answer and removed once
 * its animation has played. Keyed so React replays the animation per award
 * rather than reusing one element. */
export interface ScorePop {
  id: number;
  amount: number;
}

export interface LabGameState {
  phase: Phase;
  round: number; // 0-based
  totalRounds: number;
  question: LabQuestion | null;
  /** Which reagent the player picked this round, or null before they do. */
  picked: number | null;
  answerCorrect: boolean | null;
  score: number;
  lives: number;
  streak: number;
  maxStreak: number;
  correctCount: number;
  wrongCount: number;
  scorePops: ScorePop[];
  elapsedSeconds: number;
}

export interface LabGameApi extends LabGameState {
  /** Hands the hook a finished question set and starts round 1. */
  start: (questions: LabQuestion[]) => void;
  /** The AI is working — drives the brewing scene. */
  setBrewing: () => void;
  backToSetup: () => void;
  pickReagent: (index: number) => void;
  /** Dismisses the explanation card / advances past a finished round. */
  next: () => void;
}

/** Camera push-in on the bench before the question appears. */
const ROUND_INTRO_MS = 1300;
/** Bottle lifts, travels to the flask and empties into it. */
const POUR_MS = 1500;
/** The flask reacts — bloom on success, fizzle on failure. */
const REACT_MS = 1900;
/** The closing experiment before the stats screen. */
const FINALE_MS = 3200;

export function useLabGame(): LabGameApi {
  const [phase, setPhase] = useState<Phase>("setup");
  const [round, setRound] = useState(0);
  const [totalRounds, setTotalRounds] = useState(10);
  const [question, setQuestion] = useState<LabQuestion | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [answerCorrect, setAnswerCorrect] = useState<boolean | null>(null);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(STARTING_LIVES);
  const [streak, setStreak] = useState(0);
  const [maxStreak, setMaxStreak] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [wrongCount, setWrongCount] = useState(0);
  const [scorePops, setScorePops] = useState<ScorePop[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  /** The whole run's questions. A ref, not state: it's read inside timer
   * callbacks and never needs to trigger a render on its own. Crucially this
   * is filled ONCE per run — a round reads `questions.current[round]`, so a
   * re-render can never swap the question a player is mid-way through. */
  const questions = useRef<LabQuestion[]>([]);
  const popId = useRef(0);
  const runStartedAt = useRef(0);
  /** Mirrors `lives` for reads inside timer callbacks. State would be stale
   * there (the callback closes over the render that scheduled it), and
   * reading it through a setState updater instead would mean running phase
   * transitions inside an updater — which StrictMode double-invokes. */
  const livesRef = useRef(STARTING_LIVES);

  // Every pending timeout is tracked and cleared on unmount. This game chains
  // several per round (intro → pour → react → next), and a player closing the
  // game mid-chain must not leave one running that then setStates an
  // unmounted tree. Each timer removes its own id as it fires, so the set
  // stays the size of what's actually pending.
  const timers = useRef<Set<number>>(new Set());

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

  // Wall clock, running only while an experiment is actually in progress.
  useEffect(() => {
    if (phase === "setup" || phase === "brewing" || phase === "result") return;
    const id = window.setInterval(() => {
      setElapsedSeconds(Math.round((Date.now() - runStartedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  const beginRound = useCallback(
    (index: number) => {
      clearTimers();
      setRound(index);
      setQuestion(questions.current[index] ?? null);
      setPicked(null);
      setAnswerCorrect(null);
      setPhase("roundIntro");
      labSfx.roundStart();
      later(() => setPhase("question"), ROUND_INTRO_MS);
    },
    [clearTimers, later]
  );

  const setBrewing = useCallback(() => setPhase("brewing"), []);

  const start = useCallback(
    (qs: LabQuestion[]) => {
      clearTimers();
      questions.current = qs;
      setTotalRounds(qs.length);
      setScore(0);
      livesRef.current = STARTING_LIVES;
      setLives(STARTING_LIVES);
      setStreak(0);
      setMaxStreak(0);
      setCorrectCount(0);
      setWrongCount(0);
      setScorePops([]);
      setElapsedSeconds(0);
      runStartedAt.current = Date.now();
      beginRound(0);
    },
    [beginRound, clearTimers]
  );

  const backToSetup = useCallback(() => {
    clearTimers();
    setPhase("setup");
  }, [clearTimers]);

  /** Moves past a finished round: next round, or the closing experiment. */
  const advance = useCallback(
    (fromRound: number) => {
      const over = livesRef.current <= 0 || fromRound + 1 >= questions.current.length;
      if (!over) {
        beginRound(fromRound + 1);
        return;
      }
      // Only a run that actually reached the end earns the finale; one that
      // ran out of lives goes straight to the stats.
      if (livesRef.current > 0) {
        setPhase("finale");
        labSfx.finale();
        later(() => setPhase("result"), FINALE_MS);
      } else {
        setPhase("result");
      }
    },
    [beginRound, later]
  );

  const pickReagent = useCallback(
    (index: number) => {
      if (phase !== "question" || picked !== null) return;
      const q = questions.current[round];
      if (!q) return;

      const correct = index === q.correctIndex;
      setPicked(index);
      setPhase("pouring");
      labSfx.lift();
      later(() => labSfx.pour(), 700);

      // The verdict is decided here, at pick time, from the question that was
      // already in state — nothing is re-rolled once the bottle is moving.
      later(() => {
        setAnswerCorrect(correct);
        setPhase("reacting");

        if (correct) {
          const newStreak = streak + 1;
          const gained = scoreFor(newStreak);
          setStreak(newStreak);
          setMaxStreak((m) => Math.max(m, newStreak));
          setScore((s) => s + gained);
          setCorrectCount((c) => c + 1);
          popId.current += 1;
          const id = popId.current;
          setScorePops((p) => [...p, { id, amount: gained }]);
          // Award pops clean themselves up so the list can't grow forever
          // across a long run.
          later(() => setScorePops((p) => p.filter((x) => x.id !== id)), 1400);
          labSfx.success();
          labSfx.reward();
        } else {
          setStreak(0);
          setWrongCount((c) => c + 1);
          livesRef.current -= 1;
          setLives(livesRef.current);
          labSfx.fizzle();
        }

        // A correct answer flows straight on; a wrong one stops for the
        // explanation, which the player dismisses themselves.
        later(() => {
          if (correct) {
            advance(round);
          } else {
            setPhase("explaining");
          }
        }, REACT_MS);
      }, POUR_MS);
    },
    [advance, later, phase, picked, round, streak]
  );

  const next = useCallback(() => {
    advance(round);
  }, [advance, round]);

  return {
    phase,
    round,
    totalRounds,
    question,
    picked,
    answerCorrect,
    score,
    lives,
    streak,
    maxStreak,
    correctCount,
    wrongCount,
    scorePops,
    elapsedSeconds,
    start,
    setBrewing,
    backToSetup,
    pickReagent,
    next,
  };
}
