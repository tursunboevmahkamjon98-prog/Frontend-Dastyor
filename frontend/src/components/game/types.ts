



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


export type GameTemplate = "classic" | "race" | "goldrush" | "battle" | "classroom";

export const TEMPLATE_META: Record<GameTemplate, { label: string; emoji: string; desc: string }> = {
  classic: { label: "Классика", emoji: "⭐", desc: "Очки, жизни и серия — просто и ясно" },
  race: { label: "Гонка", emoji: "🏎️", desc: "Каждый верный ответ — рывок вперёд по трассе" },
  goldrush: { label: "Золотая лихорадка", emoji: "💰", desc: "Собирайте монеты за каждый верный ответ" },
  battle: { label: "Битва", emoji: "⚔️", desc: "Атакуйте соперника верными ответами" },
  classroom: { label: "Урок", emoji: "🏫", desc: "Тёплая школьная атмосфера, как настоящий урок у доски" },
};



export const DIFFICULTY_CONFIG: Record<Difficulty, { lives: number; timeMultiplier: number; scoreMultiplier: number; label: string }> = {
  easy: { lives: 5, timeMultiplier: 1.35, scoreMultiplier: 1, label: "Лёгкий" },
  medium: { lives: 3, timeMultiplier: 1, scoreMultiplier: 1.25, label: "Средний" },
  hard: { lives: 2, timeMultiplier: 0.75, scoreMultiplier: 1.6, label: "Сложный" },
};




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
  winner: 1 | 2 | 0; 
}

export type GameResult = SoloResult | DuelResult;





export const P1_KEYS = ["q", "w", "e", "r"];
export const P2_KEYS = ["u", "i", "o", "p"];
