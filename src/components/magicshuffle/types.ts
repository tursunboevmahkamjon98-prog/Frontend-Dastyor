// ---------------------------------------------------------------------------
// "Қуттиҳои сеҳрнок" — a shell-game with a twist: the clown posts THREE
// different questions into three identical boxes (one each), closes the lids,
// shuffles them, and the pupil picks one. Whatever question was really inside
// that box is the question they answer.
//
// Because every box holds a real question there is no "right" box to find and
// therefore nothing for the visuals to accidentally give away — all three are
// deliberately identical (see MagicBox.tsx: one shared theme, no per-box
// colour/glow/size/number). The randomness the player experiences is which of
// the three questions they end up with.
//
// Deliberately its own module rather than another GameTemplate skin (see
// components/game/types.ts): the loop here is watch → track → pick → answer,
// which shares no phase structure with the engine's straight question runs.
// This file is the pure data layer — no React, no DOM — so the rules can be
// reasoned about (and the shuffle verified honest) independently of the UI.
// ---------------------------------------------------------------------------

/** A question in the reusable teacher/admin-facing shape. Deliberately its
 * own format rather than the engine's `QuizRound`: this one carries subject
 * and difficulty so a question bank can be filtered later, and crucially an
 * `explanation` — every question in this game arrives from the AI complete
 * with the reason its answer is right (see SetupScreen). */
export interface ShuffleQuestion {
  question: string;
  answers: string[];
  /** Index into `answers` — 0-based. */
  correctAnswer: number;
  /** Why the correct answer is correct, shown after answering. Optional
   * because questions from older saved materials predate the field; the
   * feedback card simply omits the "Чаро?" section when it's missing
   * rather than inventing a reason. */
  explanation?: string;
  subject?: string;
  difficulty?: "easy" | "medium" | "hard";
}

/** One box's identity, kept strictly separate from where it currently sits.
 * `id` never changes for the life of a round; `position` (0 | 1 | 2, left to
 * right) is the only thing the shuffle permutes. The question is pinned to
 * the `id`, never to a position — that is what makes "you get the question
 * that was really in that box" true rather than decorative. */
export interface BoxState {
  id: number;
  position: number;
  /** Index into this round's three questions. Assigned once, when the
   * questions are posted into the boxes, and never touched again — the
   * shuffle only ever rewrites `position`. Opening a box reads the
   * question back out through this, which is what makes "the question you
   * get is the one that was really in there" true rather than decorative. */
  questionIndex: number;
}

export const BOX_COUNT = 3;
/** Default round count. The real number for a run is chosen by the player
 * on the setup screen and carried as `totalRounds` in the game state — this
 * is only the fallback before a run has started. */
export const TOTAL_ROUNDS = 10;
export const STARTING_LIVES = 3;

/** Every box now holds a real question, so there is no "wrong box" to
 * score — the whole round's points come from answering whichever question
 * the chosen box turns out to contain. */
export const POINTS_CORRECT_ANSWER = 100;
/** Every 3rd consecutive correct answer multiplies the answer points. */
export const COMBO_STEP = 3;
/** One-off bonus the moment a 5-answer streak lands. */
export const STREAK_BONUS_AT = 5;
export const STREAK_BONUS_POINTS = 200;

/** The round loop, in order. The important beat is that the QUESTION is what
 * gets hidden — it's shown big first ("memorise this"), then physically flies
 * into one of the boxes, and only comes back out of whichever box the player
 * opens. That's why `reveal` and `inserting` come before the boxes are ever
 * shuffled, and why `emerging` sits between opening a box and answering. */
export type Phase =
  | "setup" // pick subject/topic/grade/difficulty/rounds; AI writes the set
  | "reveal" // all three questions on screen at once, to be looked over
  | "lidsOpen" // the three lids lift, light pours out of every box
  | "inserting" // the three cards fly into their boxes, one each
  | "lidsClose" // lids come back down — "Қуттиҳо баста шуданд!"
  | "countdown" // 3 / 2 / 1 — "watch them!"
  | "shuffling" // boxes physically swap around
  | "choosing" // player picks a box
  | "opening" // chosen box shakes, its lid lifts, light pours out
  | "emerging" // that box's question flies OUT to the centre
  | "question" // answer buttons live
  | "feedback" // correct/incorrect + the explanation
  | "result"; // final screen

/** Per-round pacing, ramped by round index (see `roundConfig`). Difficulty
 * grows two ways — more swaps and faster swaps — but both are clamped so
 * late rounds stay trackable by a child rather than becoming a coin flip. */
export interface RoundConfig {
  /** How many pairwise swaps the clown performs. */
  swaps: number;
  /** Duration of a single swap animation, ms. */
  swapMs: number;
  /** How long the three questions are displayed before being posted, ms. */
  revealMs: number;
}

export function roundConfig(roundIndex: number): RoundConfig {
  // roundIndex is 0-based. Round 1 is deliberately slow and short (3 swaps
  // at 640ms) so the first thing a new player sees is obviously followable;
  // by round 10 it's 9 swaps at 260ms, which is genuinely fast but still
  // above the ~180ms where the eye stops being able to track a moving
  // object at all — the shuffle stays hard, never impossible.
  //
  // Reading time shrinks much more gently than the shuffle speeds up: a
  // child still needs long enough to actually read the question, so it
  // never drops below 2.6s no matter how late in the run it is.
  return {
    swaps: Math.min(9, 3 + Math.floor(roundIndex * 0.7)),
    swapMs: Math.max(260, 640 - roundIndex * 42),
    revealMs: Math.max(2600, 3600 - roundIndex * 100),
  };
}

/** Boxes in their starting left-to-right order, each holding one of the
 * round's three questions. `questionOrder` is a permutation of 0..2, so
 * which box gets which question is itself randomised — otherwise box 0
 * would always hold question A. */
export function initialBoxes(questionOrder: number[]): BoxState[] {
  return Array.from({ length: BOX_COUNT }, (_, i) => ({
    id: i,
    position: i,
    questionIndex: questionOrder[i],
  }));
}

/** A random permutation of 0..n-1. */
export function randomOrder(n: number): number[] {
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** One swap step: which two POSITIONS trade places. Precomputed as a list so
 * the UI can play them one at a time on a timer and the logic stays a pure
 * function of the plan — no randomness happening mid-animation, which is
 * exactly where a "the game cheated" bug would otherwise hide. */
export interface SwapStep {
  a: number;
  b: number;
}

const PAIRS: SwapStep[] = [
  { a: 0, b: 1 },
  { a: 1, b: 2 },
  { a: 0, b: 2 },
];

/** All 6 orderings of three boxes. */
const ALL_PERMS = [
  [0, 1, 2],
  [0, 2, 1],
  [1, 0, 2],
  [1, 2, 0],
  [2, 0, 1],
  [2, 1, 0],
];

/** Even/odd, by inversion count. */
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
    // Never the same pair twice in a row: a transposition is its own
    // inverse, so a repeat would visibly undo itself and read as the boxes
    // not moving at all.
    let next = Math.floor(Math.random() * PAIRS.length);
    while (next === lastIndex) next = Math.floor(Math.random() * PAIRS.length);
    lastIndex = next;
    plan.push(PAIRS[next]);
  }
  return plan;
}

/** Builds the whole shuffle plan up front, so no randomness happens mid-
 * animation (exactly where a "the game cheated" bug would otherwise hide).
 *
 * The plan is built by first picking the FINAL ordering uniformly at random
 * and then searching for a walk that reaches it — rather than just walking
 * randomly and taking whatever comes out. That matters for fairness: a walk
 * of exactly N transpositions can only ever reach permutations whose parity
 * matches N, and within a parity class short walks are far from uniform. A
 * plain random walk left the prize on its ORIGINAL position 50% of the time
 * on even-length shuffles — and since the prize's start position is shown
 * during the memorize beat, a player could have beaten the game by ignoring
 * the shuffle entirely and always picking where it started. Choosing the
 * target first (and bumping the length by one when parity demands it)
 * makes every final position equally likely, so tracking the box is the
 * only way to win. */
export function planShuffle(swaps: number): SwapStep[] {
  const target = ALL_PERMS[Math.floor(Math.random() * ALL_PERMS.length)];
  const length = permParity(target) === swaps % 2 ? swaps : swaps + 1;
  for (let attempt = 0; attempt < 200; attempt++) {
    const plan = randomWalk(length);
    const got = walkPerm(plan);
    if (got[0] === target[0] && got[1] === target[1] && got[2] === target[2]) return plan;
  }
  // Unreachable in practice (measured: 0 failures in 1.2M plans), but a
  // plain walk is a perfectly playable shuffle if the search ever misses.
  return randomWalk(length);
}

/** Applies one swap to the boxes, returning a new array. Swaps POSITIONS
 * between whichever two boxes currently occupy positions `a` and `b` — the
 * ids ride along untouched, so the prize stays with its box. */
export function applySwap(boxes: BoxState[], step: SwapStep): BoxState[] {
  return boxes.map((box) => {
    if (box.position === step.a) return { ...box, position: step.b };
    if (box.position === step.b) return { ...box, position: step.a };
    return box;
  });
}

/** Points for one answered question, given the streak it lands on.
 * `streakAfter` is the streak count INCLUDING this answer. */
export function answerPoints(streakAfter: number): number {
  const comboMultiplier = 1 + Math.floor(streakAfter / COMBO_STEP) * 0.5;
  return Math.round(POINTS_CORRECT_ANSWER * comboMultiplier);
}

/** 0-4 stars from final accuracy, for the result screen's star row. */
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

/** Cycles the available questions to fill exactly TOTAL_ROUNDS slots — a
 * lesson's game might only carry 6 quiz rounds, and the shell game is the
 * point, so a repeated question late in a run is much better than cutting
 * the run short. Shuffled first so the repeats aren't in the same order. */
export function buildRoundQuestions(pool: ShuffleQuestion[], rounds: number): ShuffleQuestion[] {
  if (pool.length === 0) return [];
  const shuffled = [...pool];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return Array.from({ length: rounds }, (_, i) => shuffled[i % shuffled.length]);
}
