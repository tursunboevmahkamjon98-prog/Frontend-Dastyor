export type LessonFrameworkId = "gagne" | "boppps" | "fivee";

export interface LessonFrameworkOption {
  id: LessonFrameworkId;
  names: { ru: string; tg: string; en: string };
  descriptions: { ru: string; tg: string; en: string };
  stages: string[];
  guidance: string;
}

/**
 * Lesson Loom's instructional-design choices, kept as a small Dastyor data
 * module. The framework shapes lesson stages and activities; it never replaces
 * Dastyor's konspekt schema or its material-specific output.
 */
export const LESSON_FRAMEWORKS: LessonFrameworkOption[] = [
  {
    id: "gagne",
    names: {
      ru: "Девять событий Ганье",
      tg: "Нӯҳ рӯйдоди Ганье",
      en: "Gagné's Nine Events",
    },
    descriptions: {
      ru: "Пошаговая структура: внимание, цели, объяснение, практика, обратная связь и перенос.",
      tg: "Сохтори пайдарпай: диққат, мақсад, шарҳ, машқ, фикру мулоҳиза ва истифода.",
      en: "A step-by-step structure: attention, objectives, explanation, practice, feedback and transfer.",
    },
    stages: [
      "Gain attention",
      "Inform learners of objectives",
      "Stimulate recall",
      "Present the content",
      "Provide guidance",
      "Elicit performance",
      "Provide feedback",
      "Assess performance",
      "Enhance retention and transfer",
    ],
    guidance:
      "Use the nine events in order. Give meaningful time to practice and feedback; do not let explanation take the whole lesson.",
  },
  {
    id: "boppps",
    names: { ru: "BOPPPS", tg: "BOPPPS", en: "BOPPPS" },
    descriptions: {
      ru: "Вход в тему, цели, предварительная проверка, активная работа, итоговая проверка и вывод.",
      tg: "Оғози мавзӯъ, мақсад, санҷиши аввал, кори фаъол, санҷиши ниҳоӣ ва хулоса.",
      en: "Bridge-in, objectives, pre-test, participatory learning, post-test and summary.",
    },
    stages: ["Bridge-in", "Objectives", "Pre-test", "Participatory learning", "Post-test", "Summary"],
    guidance:
      "Use a short pre-check and a directly aligned post-check. Participatory learning should take most of the lesson.",
  },
  {
    id: "fivee",
    names: { ru: "Модель 5E", tg: "Модели 5E", en: "5E Model" },
    descriptions: {
      ru: "Вовлечение, исследование, объяснение, применение и оценивание.",
      tg: "Ҷалбкунӣ, таҳқиқ, шарҳ, истифода ва арзёбӣ.",
      en: "Engage, explore, explain, elaborate and evaluate.",
    },
    stages: ["Engage", "Explore", "Explain", "Elaborate", "Evaluate"],
    guidance:
      "Explore must come before Explain. Learners investigate first, then the teacher builds the explanation from their findings.",
  },
];

export function lessonLanguageKey(language: string): "ru" | "tg" | "en" {
  if (language === "Таджикский") return "tg";
  if (language === "Английский") return "en";
  return "ru";
}

export function lessonFrameworkFor(id: LessonFrameworkId): LessonFrameworkOption {
  return LESSON_FRAMEWORKS.find((framework) => framework.id === id) ?? LESSON_FRAMEWORKS[0];
}

