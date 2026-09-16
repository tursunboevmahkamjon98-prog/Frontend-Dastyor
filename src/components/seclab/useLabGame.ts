"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LabQuestion, Phase, STARTING_LIVES, scoreFor } from "./types";
import { labSfx } from "./sounds";


export interface ScorePop {
  id: number;
  amount: number;
}

export interface LabGameState {
  phase: Phase;
  round: number; 
  totalRounds: number;
  question: LabQuestion | null;
  
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
  
  start: (questions: LabQuestion[]) => void;
  
  setBrewing: () => void;
  backToSetup: () => void;
  pickReagent: (index: number) => void;
  
  next: () => void;
}


const ROUND_INTRO_MS = 1300;

const POUR_MS = 1500;

const REACT_MS = 1900;

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

  
  const questions = useRef<LabQuestion[]>([]);
  const popId = useRef(0);
  const runStartedAt = useRef(0);
  
  const livesRef = useRef(STARTING_LIVES);

  
  
  
  
  
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

  
  const advance = useCallback(
    (fromRound: number) => {
      const over = livesRef.current <= 0 || fromRound + 1 >= questions.current.length;
      if (!over) {
        beginRound(fromRound + 1);
        return;
      }
      
      
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
