










export interface LabQuestion {
  question: string;
  
  options: string[];
  correctIndex: number;
  explanation: string;
}

export const STARTING_LIVES = 3;
export const POINTS_PER_CORRECT = 50;

export const COMBO_STEP = 3;

export type Phase =
  | "setup" 
  | "brewing" 
  | "roundIntro" 
  | "question" 
  | "pouring" 
  | "reacting" 
  | "explaining" 
  | "finale" 
  | "result"; 


export const STATIONS = [
  "Даромадгоҳ",
  "Мизи корӣ",
  "Микроскоп",
  "Реаксия",
  "Таҳлил",
  "Формулаи ниҳоӣ",
] as const;


export function stationForRound(round: number, totalRounds: number): number {
  if (totalRounds <= 1) return 0;
  return Math.min(STATIONS.length - 1, Math.floor((round / totalRounds) * STATIONS.length));
}


export function scoreFor(streakAfter: number): number {
  const combo = 1 + Math.floor(streakAfter / COMBO_STEP) * 0.5;
  return Math.round(POINTS_PER_CORRECT * combo);
}


export interface ReactionConfig {
  
  bubbles: number;
  
  sparks: number;
  
  intensity: number;
}

export function reactionConfig(round: number, totalRounds: number): ReactionConfig {
  const t = totalRounds <= 1 ? 1 : round / (totalRounds - 1); 
  return {
    bubbles: Math.round(6 + t * 10),
    sparks: Math.round(10 + t * 14),
    intensity: 0.55 + t * 0.45,
  };
}


export const REAGENT_COLORS = [
  { liquid: "#38bdf8", glow: "#38bdf8", deep: "#0369a1" }, 
  { liquid: "#a855f7", glow: "#a855f7", deep: "#6b21a8" }, 
  { liquid: "#34d399", glow: "#34d399", deep: "#047857" }, 
  { liquid: "#fb923c", glow: "#fb923c", deep: "#c2410c" }, 
];

export const OPTION_LETTERS = ["A", "B", "C", "D"];


export function fromQuizSet(
  raw: { question: string; options: string[]; correct_index: number; explanation: string }[]
): LabQuestion[] {
  const out: LabQuestion[] = [];
  for (const q of raw) {
    if (!q.question || !Array.isArray(q.options) || q.options.length < 2) continue;
    
    
    
    
    
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
