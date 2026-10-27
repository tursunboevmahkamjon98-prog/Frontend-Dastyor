



















export interface ShuffleQuestion {
  question: string;
  answers: string[];
  
  correctAnswer: number;
  
  explanation?: string;
  subject?: string;
  difficulty?: "easy" | "medium" | "hard";
}


export interface BoxState {
  id: number;
  position: number;
  
  questionIndex: number;
}

export const BOX_COUNT = 3;

export const TOTAL_ROUNDS = 10;
export const STARTING_LIVES = 3;


export const POINTS_CORRECT_ANSWER = 100;

export const COMBO_STEP = 3;

export const STREAK_BONUS_AT = 5;
export const STREAK_BONUS_POINTS = 200;


export type Phase =
  | "setup" 
  | "reveal" 
  | "lidsOpen" 
  | "inserting" 
  | "lidsClose" 
  | "countdown" 
  | "shuffling" 
  | "choosing" 
  | "opening" 
  | "emerging" 
  | "question" 
  | "feedback" 
  | "result"; 


export interface RoundConfig {
  
  swaps: number;
  
  swapMs: number;
  
  revealMs: number;
}

export function roundConfig(roundIndex: number): RoundConfig {
  
  
  
  
  
  
  
  
  
  return {
    swaps: Math.min(9, 3 + Math.floor(roundIndex * 0.7)),
    swapMs: Math.max(260, 640 - roundIndex * 42),
    revealMs: Math.max(2600, 3600 - roundIndex * 100),
  };
}


export function initialBoxes(questionOrder: number[]): BoxState[] {
  return Array.from({ length: BOX_COUNT }, (_, i) => ({
    id: i,
    position: i,
    questionIndex: questionOrder[i],
  }));
}


export function randomOrder(n: number): number[] {
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}


export interface SwapStep {
  a: number;
  b: number;
}

const PAIRS: SwapStep[] = [
  { a: 0, b: 1 },
  { a: 1, b: 2 },
  { a: 0, b: 2 },
];


const ALL_PERMS = [
  [0, 1, 2],
  [0, 2, 1],
  [1, 0, 2],
  [1, 2, 0],
  [2, 0, 1],
  [2, 1, 0],
];


function permParity(p: number[]): number {
  let inversions = 0;
  for (let i = 0; i < p.length; i++) {
    for (let j = i + 1; j < p.length; j++) if (p[i] > p[j]) inversions++;
  }
  return inversions % 2;
}

function walkPerm(plan: SwapStep[]): number[] {
  const p = [0, 1, 2];
  for (const s of plan) [p[s.a], p[s.b]] = [p[s.b], p[s.a]];
  return p;
}

function randomWalk(length: number): SwapStep[] {
  const plan: SwapStep[] = [];
  let lastIndex = -1;
  for (let i = 0; i < length; i++) {
    
    
    
    let next = Math.floor(Math.random() * PAIRS.length);
    while (next === lastIndex) next = Math.floor(Math.random() * PAIRS.length);
    lastIndex = next;
    plan.push(PAIRS[next]);
  }
  return plan;
}


export function planShuffle(swaps: number): SwapStep[] {
  const target = ALL_PERMS[Math.floor(Math.random() * ALL_PERMS.length)];
  const length = permParity(target) === swaps % 2 ? swaps : swaps + 1;
  for (let attempt = 0; attempt < 200; attempt++) {
    const plan = randomWalk(length);
    const got = walkPerm(plan);
    if (got[0] === target[0] && got[1] === target[1] && got[2] === target[2]) return plan;
  }
  
  
  return randomWalk(length);
}


export function applySwap(boxes: BoxState[], step: SwapStep): BoxState[] {
  return boxes.map((box) => {
    if (box.position === step.a) return { ...box, position: step.b };
    if (box.position === step.b) return { ...box, position: step.a };
    return box;
  });
}


export function answerPoints(streakAfter: number): number {
  const comboMultiplier = 1 + Math.floor(streakAfter / COMBO_STEP) * 0.5;
  return Math.round(POINTS_CORRECT_ANSWER * comboMultiplier);
}


export function starsFor(correct: number, total: number): number {
  if (total === 0) return 0;
  const pct = correct / total;
  if (pct >= 0.95) return 5;
  if (pct >= 0.8) return 4;
  if (pct >= 0.6) return 3;
  if (pct >= 0.4) return 2;
  if (pct > 0) return 1;
  return 0;
}


export function buildRoundQuestions(pool: ShuffleQuestion[], rounds: number): ShuffleQuestion[] {
  if (pool.length === 0) return [];
  const shuffled = [...pool];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return Array.from({ length: rounds }, (_, i) => shuffled[i % shuffled.length]);
}
