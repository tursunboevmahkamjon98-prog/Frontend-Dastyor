// ---------------------------------------------------------------------------
// "Лабораторияи махфӣ" — a secret-laboratory quiz game. Each round the AI
// poses one question and the bench fills with reagent bottles, one per answer
// option. Picking a bottle physically carries it to the big flask and pours
// it in; the reaction that follows is the feedback.
//
// This file is the pure data layer — no React, no DOM — so the rules can be
// reasoned about independently of the scene.
// ---------------------------------------------------------------------------

/** One AI-written question. Mirrors the backend's QuizSetQuestion (see
 * ai_service.generate_quiz_set) but in the shape this game reads, and with
 * the explanation promoted to a required field: a wrong answer here ALWAYS
 * shows why the right one is right, so a question without one would leave a
 * hole in the game's main teaching moment. */
export interface LabQuestion {
  question: string;
  /** One entry per reagent bottle on the bench. */
  options: string[];
  correctIndex: number;
  explanation: string;
}

export const STARTING_LIVES = 3;
export const POINTS_PER_CORRECT = 50;
/** Every 3rd correct answer in a row multiplies the award. */
export const COMBO_STEP = 3;

export type Phase =
  | "setup" // subject/topic/grade/difficulty/count
  | "brewing" // AI is writing the questions
  | "roundIntro" // "Таҷрибаи нав!" — camera pushes in on the bench
  | "question" // question panel + reagents, waiting for a pick
  | "pouring" // chosen bottle travels to the flask and empties into it
  | "reacting" // the flask reacts: success bloom or fizzle
  | "explaining" // wrong answer only: correct answer + why
  | "finale" // all stations light up, the big experiment completes
  | "result"; // staged stats

/** The lab "stations" a run travels through — the visual progress journey.
 * Purely cosmetic: a run always has `totalRounds` rounds, and this maps
 * however many that is onto a fixed six-stop path so the journey reads the
 * same whether the player chose 5 questions or 20. */
export const STATIONS = [
  "Даромадгоҳ",
  "Мизи корӣ",
  "Микроскоп",
  "Реаксия",
  "Таҳлил",
  "Формулаи ниҳоӣ",
] as const;

/** Which station index a given round sits at. */
export function stationForRound(round: number, totalRounds: number): number {
  if (totalRounds <= 1) return 0;
  return Math.min(STATIONS.length - 1, Math.floor((round / totalRounds) * STATIONS.length));
}

/** Points for one correct answer, given the streak it lands on (streak
 * INCLUDING this answer). */
export function scoreFor(streakAfter: number): number {
  const combo = 1 + Math.floor(streakAfter / COMBO_STEP) * 0.5;
  return Math.round(POINTS_PER_CORRECT * combo);
}

/** How elaborate the reaction looks, ramped by round. The QUESTION difficulty
 * is fixed by the player's own setting and never touched here — this is
 * purely how much spectacle the flask produces, so a late round feels like a
 * bigger experiment without secretly making the quiz harder than asked. */
export interface ReactionConfig {
  /** Bubbles rising in the flask during a reaction. */
  bubbles: number;
  /** Particles thrown out on a correct answer. */
  sparks: number;
  /** Glow strength, 0..1. */
  intensity: number;
}

export function reactionConfig(round: number, totalRounds: number): ReactionConfig {
  const t = totalRounds <= 1 ? 1 : round / (totalRounds - 1); // 0..1
  return {
    bubbles: Math.round(6 + t * 10),
    sparks: Math.round(10 + t * 14),
    intensity: 0.55 + t * 0.45,
  };
}

/** Liquid colours for the reagent bottles, by option index. These are
 * decorative only — the correct bottle is NOT identifiable by colour,
 * because the colours are assigned by position on the bench, never by
 * correctness, and the option order the AI returns is used as-is. */
export const REAGENT_COLORS = [
  { liquid: "#38bdf8", glow: "#38bdf8", deep: "#0369a1" }, // cyan
  { liquid: "#a855f7", glow: "#a855f7", deep: "#6b21a8" }, // violet
  { liquid: "#34d399", glow: "#34d399", deep: "#047857" }, // green
  { liquid: "#fb923c", glow: "#fb923c", deep: "#c2410c" }, // amber
];

export const OPTION_LETTERS = ["A", "B", "C", "D"];

/** Converts the backend's quiz-set payload into this game's question shape,
 * dropping anything malformed rather than letting a broken entry become an
 * unanswerable round. */
export function fromQuizSet(
  raw: { question: string; options: string[]; correct_index: number; explanation: string }[]
): LabQuestion[] {
  const out: LabQuestion[] = [];
  for (const q of raw) {
    if (!q.question || !Array.isArray(q.options) || q.options.length < 2) continue;
    // Cap at 4: the bench is built for at most four bottles, and the
    // generator is asked for exactly four. The index is validated against
    // the SLICED list — checking it against the original length first would
    // let a correct answer at position 5 survive the slice and leave a
    // round whose right answer isn't on the bench at all.
    const options = q.options.slice(0, 4);
    if (typeof q.correct_index !== "number" || q.correct_index < 0 || q.correct_index >= options.length) continue;
    out.push({
      question: q.question,
      options,
      correctIndex: q.correct_index,
      explanation: q.explanation ?? "",
    });
  }
  return out;
}
