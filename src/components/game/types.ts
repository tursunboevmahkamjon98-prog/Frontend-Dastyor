// Shared round shapes — mirrors backend/app/ai_service.py's _GAME_ROUND_SHAPES
// exactly (same 5 types, same fields). One union rather than five arrays so
// every game screen (solo/duel/results) dispatches on `round.type` instead of
// each carrying its own copy of this list.
export interface QuizRound {
  type: "quiz";
  question: string;
  options: string[];
  correct_index: number;
}
export interface TrueFalseRound {
  type: "true_false";
  statement: string;
  answer: boolean;
}
export interface MatchingRound {
  type: "matching";
  instructions?: string;
  pairs: { left: string; right: string }[];
}
export interface OrderRound {
  type: "order";
  instructions?: string;
  items: string[];
}
export interface SpeedRound {
  type: "speed";
  question: string;
  answer: string;
  time_limit_seconds?: number;
}
export type Round = QuizRound | TrueFalseRound | MatchingRound | OrderRound | SpeedRound;

export type GamePhase = "start" | "solo" | "duel" | "result";
export type GameMode = "solo" | "duel";
export type Difficulty = "easy" | "medium" | "hard";

/** Visual/mechanical "skin" over the exact same round-answering core
 * (quiz/true_false/matching/order/speed content, scoring, lives) — same
 * idea as Blooket's game modes: the question widget never changes, only
 * how progress reads on screen. "classic" is the plain HUD the engine
 * shipped with first; the other three each replace just that HUD/progress
 * area (see components/game/templates.tsx) in both SoloGame and
 * DuelGame. Picked once on the start screen, before mode. */
export type GameTemplate = "classic" | "race" | "goldrush" | "battle" | "classroom";

export const TEMPLATE_META: Record<GameTemplate, { label: string; emoji: string; desc: string }> = {
  classic: { label: "Классика", emoji: "⭐", desc: "Очки, жизни и серия — просто и ясно" },
  race: { label: "Гонка", emoji: "🏎️", desc: "Каждый верный ответ — рывок вперёд по трассе" },
  goldrush: { label: "Золотая лихорадка", emoji: "💰", desc: "Собирайте монеты за каждый верный ответ" },
  battle: { label: "Битва", emoji: "⚔️", desc: "Атакуйте соперника верными ответами" },
  classroom: { label: "Урок", emoji: "🏫", desc: "Тёплая школьная атмосфера, как настоящий урок у доски" },
};


/** Per-difficulty starting knobs for solo play — chosen once on the start
 * screen, then SoloGame.tsx ramps further within a run (see LEVEL_SIZE
 * there) so difficulty is both a pre-game choice and something that grows
 * as the round progresses, per product ask. */
export const DIFFICULTY_CONFIG: Record<Difficulty, { lives: number; timeMultiplier: number; scoreMultiplier: number; label: string }> = {
  easy: { lives: 5, timeMultiplier: 1.35, scoreMultiplier: 1, label: "Лёгкий" },
  medium: { lives: 3, timeMultiplier: 1, scoreMultiplier: 1.25, label: "Средний" },
  hard: { lives: 2, timeMultiplier: 0.75, scoreMultiplier: 1.6, label: "Сложный" },
};

// Base answer-window per round type before difficulty/level scaling —
// matching/order have no hard timer (they're self-paced puzzles) so they
// carry a *target* time for the speed bonus rather than a fail-on-timeout.
export const BASE_TIME_SECONDS: Record<Round["type"], number> = {
  quiz: 12,
  true_false: 8,
  matching: 25,
  order: 20,
  speed: 15,
};

export interface SoloResult {
  mode: "solo";
  won: boolean;
  score: number;
  level: number;
  maxStreak: number;
  roundsCleared: number;
  totalRounds: number;
  badges: string[];
}

export interface DuelResult {
  mode: "duel";
  scoreP1: number;
  scoreP2: number;
  winner: 1 | 2 | 0; // 0 = tie
}

export type GameResult = SoloResult | DuelResult;

// P1 uses the left hand's top row, P2 the right hand's — far enough apart
// on a physical keyboard that two kids' hands don't collide reaching for
// them. Index 0/1 double as True/Verno and False/Neverno for true_false
// rounds, and index 0 alone doubles as the "buzz" key for speed rounds.
export const P1_KEYS = ["q", "w", "e", "r"];
export const P2_KEYS = ["u", "i", "o", "p"];
