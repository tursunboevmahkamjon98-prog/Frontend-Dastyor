import { ContentLanguage, normalizeContentLanguage } from "./content-lang";

export const KONSPEKT_SECTION_KEYS = [
  "competencies",
  "objectives",
  "key_concepts",
  "key_terms",
  "lesson_program",
  "tools",
  "warmup",
  "main_content",
  "real_life_examples",
  "visual_aid",
  "pair_work",
  "consolidation",
  "fun_facts",
  "common_mistakes",
  "summary",
  "homework",
  "assessment",
] as const;

type SectionKey = (typeof KONSPEKT_SECTION_KEYS)[number];

interface KonspektStrings {
  toc: string;
  regenerateSection: string;
  loadingPhoto: string;
  loadPhoto: string;
  findingPhoto: string;
  replacePhoto: string;
  uploadingPhoto: string;
  ownPhoto: string;
  sections: Record<SectionKey, string>;
}

const RU: KonspektStrings = {
  toc: "Содержание",
  regenerateSection: "Пересоздать этот раздел заново",
  loadingPhoto: "Загружаем фото…",
  loadPhoto: "Загрузить фото",
  findingPhoto: "Ищем другое фото…",
  replacePhoto: "Заменить фото",
  uploadingPhoto: "Загружаем…",
  ownPhoto: "Своё фото",
  sections: {
    competencies: "Компетенции",
    objectives: "Цели урока",
    key_concepts: "Ключевые понятия",
    key_terms: "Термины",
    lesson_program: "План урока",
    tools: "Инструменты",
    warmup: "Разминка",
    main_content: "Основное содержание",
    real_life_examples: "Примеры из жизни",
    visual_aid: "Наглядные материалы",
    pair_work: "Работа в парах",
    consolidation: "Закрепление",
    fun_facts: "Интересные факты",
    common_mistakes: "Частые ошибки",
    summary: "Итоги урока",
    homework: "Домашнее задание",
    assessment: "Критерии оценки",
  },
};

const TG: KonspektStrings = {
  toc: "Мундариҷа",
  regenerateSection: "Аз нав эҷод кардани ин бахш",
  loadingPhoto: "Сурат бор карда мешавад…",
  loadPhoto: "Сурат боргирӣ кардан",
  findingPhoto: "Ҷустуҷӯи сурати дигар…",
  replacePhoto: "Иваз кардани сурат",
  uploadingPhoto: "Бор карда мешавад…",
  ownPhoto: "Сурати худ",
  sections: {
    competencies: "Салоҳиятҳо",
    objectives: "Ҳадафҳои дарс",
    key_concepts: "Мафҳумҳои калидӣ",
    key_terms: "Истилоҳот",
    lesson_program: "Нақшаи дарс",
    tools: "Абзорҳо",
    warmup: "Гармкунӣ",
    main_content: "Мазмуни асосӣ",
    real_life_examples: "Мисолҳо аз ҳаёт",
    visual_aid: "Маводи аёнӣ",
    pair_work: "Кор дар ҷуфтҳо",
    consolidation: "Мустаҳкамкунӣ",
    fun_facts: "Далелҳои ҷолиб",
    common_mistakes: "Хатогиҳои маъмул",
    summary: "Хулосаи дарс",
    homework: "Вазифаи хонагӣ",
    assessment: "Меъёрҳои баҳогузорӣ",
  },
};

const EN: KonspektStrings = {
  toc: "Contents",
  regenerateSection: "Regenerate this section",
  loadingPhoto: "Loading photo…",
  loadPhoto: "Load photo",
  findingPhoto: "Finding another photo…",
  replacePhoto: "Replace photo",
  uploadingPhoto: "Uploading…",
  ownPhoto: "Own photo",
  sections: {
    competencies: "Competencies",
    objectives: "Lesson objectives",
    key_concepts: "Key concepts",
    key_terms: "Key terms",
    lesson_program: "Lesson plan",
    tools: "Tools",
    warmup: "Warm-up",
    main_content: "Main content",
    real_life_examples: "Real-life examples",
    visual_aid: "Visual aids",
    pair_work: "Pair work",
    consolidation: "Consolidation",
    fun_facts: "Fun facts",
    common_mistakes: "Common mistakes",
    summary: "Lesson summary",
    homework: "Homework",
    assessment: "Assessment criteria",
  },
};

const BY_LANGUAGE: Record<ContentLanguage, KonspektStrings> = {
  "Русский": RU,
  "Таджикский": TG,
  "Английский": EN,
};

export function getKonspektStrings(language?: string | null): KonspektStrings {
  return BY_LANGUAGE[normalizeContentLanguage(language)];
}

export function konspektSectionLabel(key: string, language?: string | null): string {
  const strings = getKonspektStrings(language);
  return strings.sections[key as SectionKey] ?? key;
}
