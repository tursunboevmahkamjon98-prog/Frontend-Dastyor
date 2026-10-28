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


export interface ShuffleGameState {
  phase: Phase;
  round: number; 
  boxes: BoxState[];
  
  roundQuestions: ShuffleQuestion[];
  countdownStep: number; 
  pickedBoxId: number | null;
  
  activeQuestion: ShuffleQuestion | null;
  pickedAnswer: number | null;
  answerCorrect: boolean | null;
  score: number;
  lives: number;
  streak: number;
  maxStreak: number;
  correctAnswers: number;
  questionsAnswered: number;
  
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

const LIDS_OPEN_MS = 900;

const INSERT_MS = 1500;

const LIDS_CLOSE_MS = 1100;

const OPENING_MS = 950;

const EMERGE_MS = 950;


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

  
  const pool = useRef<ShuffleQuestion[]>([]);

  
  
  
  
  
  
  
  
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

  
  
  
  useEffect(() => {
    if (phase === "setup" || phase === "result") return;
    const id = window.setInterval(() => {
      setElapsedSeconds(Math.round((Date.now() - runStartedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [phase]);

  
  const beginRound = useCallback(
    (roundIndex: number) => {
      
      
      
      clearTimers();
      const cfg = roundConfig(roundIndex);

      
      
      const slice = pool.current.slice(roundIndex * BOX_COUNT, roundIndex * BOX_COUNT + BOX_COUNT);
      setRoundQuestions(slice);
      let working = initialBoxes(randomOrder(BOX_COUNT));

      setBoxes(working);
      setPickedBoxId(null);
      setPickedAnswer(null);
      setAnswerCorrect(null);
      setPhase("reveal");
      magicSfx.wand();

      
      later(() => {
        
        setPhase("lidsOpen");
        magicSfx.lidOpen();

        later(() => {
          
          setPhase("inserting");
          magicSfx.wand();

          later(() => {
            
            setPhase("lidsClose");
            magicSfx.lidClose();

            later(() => {
              
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

  
  const next = useCallback(() => {
    setComboToast(null);
    
    
    
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
