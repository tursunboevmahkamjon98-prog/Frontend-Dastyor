import { BookOpen, Presentation, ClipboardCheck, Lightbulb, ClipboardList, Gamepad2 } from "lucide-react";
import type { MaterialType } from "./api";
import type { MessageKey } from "./messages";

export const MATERIAL_TYPE_CONFIG: Record<
  MaterialType,
  { label: string; icon: typeof BookOpen; bg: string; color: string }
> = {
  konspekt: { label: "Конспект", icon: BookOpen, bg: "bg-note-bg", color: "text-note-icon" },
  lektsiya: { label: "Лекция", icon: Lightbulb, bg: "bg-lecture-bg", color: "text-lecture-icon" },
  test: { label: "Тест", icon: ClipboardCheck, bg: "bg-test-bg", color: "text-test-icon" },
  prezentatsiya: { label: "Презентация", icon: Presentation, bg: "bg-pres-bg", color: "text-pres-icon" },
  
  
  
  
  amaliy: { label: "Практические задания", icon: ClipboardList, bg: "bg-amaliy-bg", color: "text-amaliy-icon" },
  igra: { label: "Игра", icon: Gamepad2, bg: "bg-igra-bg", color: "text-igra-icon" },
};

export const MATERIAL_TYPES: MaterialType[] = ["konspekt", "lektsiya", "test", "prezentatsiya", "amaliy", "igra"];


export const LIBRARY_TYPES = MATERIAL_TYPES.filter(
  (t): t is Exclude<MaterialType, "igra"> => t !== "igra"
);


export const CREATABLE_TYPES: MaterialType[] = MATERIAL_TYPES.filter(
  (t): t is Exclude<MaterialType, "igra"> => t !== "igra"
);


export const MATERIAL_TYPE_LABEL_KEY: Record<MaterialType, MessageKey> = {
  konspekt: "type.konspekt",
  lektsiya: "type.lektsiya",
  test: "type.test",
  prezentatsiya: "type.prezentatsiya",
  amaliy: "type.amaliy",
  igra: "type.igra",
};


export const MATERIAL_TYPE_LABEL_ACC_KEY: Record<MaterialType, MessageKey> = {
  konspekt: "type.konspektAcc",
  lektsiya: "type.lektsiyaAcc",
  test: "type.testAcc",
  prezentatsiya: "type.prezentatsiyaAcc",
  amaliy: "type.amaliyAcc",
  igra: "type.igraAcc",
};





export const LANGUAGES = ["Русский", "Таджикский", "Английский"];
export const LEVELS = ["Лёгкий", "Средний", "Сложный"];


export const LANGUAGE_LABEL_KEYS: Record<string, MessageKey> = {
  "Русский": "value.langRu",
  "Таджикский": "value.langTg",
  "Английский": "value.langEn",
};

export const LEVEL_LABEL_KEYS: Record<string, MessageKey> = {
  "Лёгкий": "value.levelEasy",
  "Средний": "value.levelMedium",
  "Сложный": "value.levelHard",
};

export const CLASSES = Array.from({ length: 11 }, (_, i) => `${i + 1} класс`);




export const SUBJECTS = [
  "Математика",
  "Алгебра",
  "Геометрия",
  "Информатика",
  "Физика",
  "Химия",
  "Биология",
  "География",
  "Русский язык",
  "Английский язык",
  "Таджикский язык",
  "Таджикская литература",
  "История Таджикистана",
  "Всемирная история",
];








export const KONSPEKT_TEMPLATES: {
  id: string;
  name: string;
  description: string;
  mockup: { accent: string; header: "bar" | "underline" | "numbered" | "smallcaps" | "serif" };
}[] = [
  { id: "klassik", name: "Классический", description: "Пронумерованные разделы, цветные карточки", mockup: { accent: "#2a78d6", header: "numbered" } },
  { id: "zamonaviy", name: "Современный", description: "Понятия и термины — в панели сверху", mockup: { accent: "#fb7185", header: "underline" } },
  { id: "minimal", name: "Минимализм", description: "Чистая типографика, без заливки", mockup: { accent: "#6b7280", header: "smallcaps" } },
  { id: "rasmiy", name: "Официальный", description: "Академический стиль, засечный шрифт", mockup: { accent: "#8a2635", header: "serif" } },
  { id: "rangli", name: "Яркий", description: "Разделы на цветных плашках", mockup: { accent: "#10b981", header: "bar" } },
  { id: "nakscha", name: "Нақшаи тавзеҳотӣ", description: "Официальный школьный бланк: без цвета, разделы в строку", mockup: { accent: "#334155", header: "smallcaps" } },
];


export const LECTURE_TEMPLATES: {
  id: string;
  name: string;
  description: string;
  page: {
    cover: "none" | "classic" | "split" | "banner" | "worksheet";
    heading: "runin" | "smallcaps" | "ghost" | "band" | "boxed";
    callout: "inline" | "rule" | "card" | "outline" | "dashed";
    serif: boolean;
    quiet: boolean;
    
    notebook_grid?: boolean;
  };
}[] = [
  {
    id: "planspekt",
    name: "План-конспект",
    description: "Лаконичный рабочий формат: шапка-бланк, разделы в строку, без обложки",
    page: { cover: "none", heading: "runin", callout: "inline", serif: false, quiet: true },
  },
  {
    id: "playful",
    name: "Яркий блокнот",
    description: "Разноцветные карточки-ленты на бумаге в линейку: цель, слова, формулы, вывод — на одном листе",
    page: { cover: "none", heading: "runin", callout: "card", serif: false, quiet: false, notebook_grid: true },
  },
  {
    id: "kitob",
    name: "Современный",
    description: "Цветная панель на обложке, крупные номера разделов, определения карточками",
    page: { cover: "split", heading: "ghost", callout: "card", serif: false, quiet: false },
  },
  {
    id: "akademik",
    name: "Академический",
    description: "Титульный лист, засечный шрифт, римские цифры, тонкие линии без заливок",
    page: { cover: "classic", heading: "smallcaps", callout: "rule", serif: true, quiet: true },
  },
  {
    id: "jurnal",
    name: "Журнальный",
    description: "Баннер на обложке, разделы на цветной плашке, ключевые мысли крупно",
    page: { cover: "banner", heading: "band", callout: "outline", serif: true, quiet: false },
  },
  {
    id: "praktikum",
    name: "Практикум",
    description: "Рабочий лист: рамка и поля для имени, место для записей в самопроверке",
    page: { cover: "worksheet", heading: "boxed", callout: "dashed", serif: false, quiet: false },
  },
];


export const PRESENTATION_TEMPLATES: {
  id: string;
  name: string;
  description: string;
  deck: {
    header: "rule" | "underline" | "band" | "plain";
    cards: boolean;
    badge: boolean;
    paper: string;
    ink: string;
    serif?: boolean;
    caps?: boolean;
    
    pastel?: boolean;
  };
}[] = [
  
  
  
  
  
  
  
  
  {
    id: "playful",
    name: "Яркий блокнот",
    description: "Пастельные разноцветные карточки, поля как в тетради, рукописный заголовок",
    deck: { header: "rule", cards: true, badge: true, paper: "#fffdf7", ink: "#2d2a4a", pastel: true },
  },
  {
    id: "zamonaviy",
    name: "Современная школа",
    description: "Белый фон, тезисы — карточки с цветным значком и рамкой",
    deck: { header: "rule", cards: true, badge: true, paper: "#ffffff", ink: "#1e2937" },
  },
  {
    id: "google",
    name: "Google Slides",
    description: "Белый фон, простая линия под заголовком, обычные тезисы без плашек",
    deck: { header: "underline", cards: false, badge: false, paper: "#ffffff", ink: "#202124" },
  },
  {
    id: "klassik",
    name: "Академический",
    description: "Тёплая бумага, засечный шрифт, линии вместо плашек",
    deck: { header: "underline", cards: false, badge: false, paper: "#fcfaf5", ink: "#1f1b16", serif: true },
  },
  {
    id: "rangli",
    name: "Цветной класс",
    description: "Цветная полоса с заголовком, тезисы карточками",
    deck: { header: "band", cards: true, badge: true, paper: "#ffffff", ink: "#111827" },
  },
  {
    id: "minimal",
    name: "Минимализм",
    description: "Только текст и воздух: без плашек и значков",
    deck: { header: "plain", cards: false, badge: false, paper: "#ffffff", ink: "#0f172a", caps: true },
  },
];





const SUBJECT_ACCENTS: Record<string, string> = {
  "Таджикский язык": "#0e7c86",
  "Таджикская литература": "#6b3fa0",
  "Русский язык": "#c62839",
  "Английский язык": "#1d5fc2",
  "Математика": "#4a3aa7",
  "Алгебра": "#7c3aed",
  "Геометрия": "#0f9b6e",
  "Информатика": "#2a78d6",
  "Физика": "#eb6834",
  "Химия": "#0891b2",
  "Биология": "#008300",
  "География": "#a3702d",
  "История Таджикистана": "#8a2635",
  "Всемирная история": "#b5502e",
};
const DEFAULT_ACCENT = "#3B82F6";

export function getSubjectAccent(subject: string | null | undefined): string {
  return (subject && SUBJECT_ACCENTS[subject]) || DEFAULT_ACCENT;
}






export const TEST_TYPES = [
  { value: "mixed", label: "Смешанный" },
  { value: "multiple_choice", label: "Один правильный ответ" },
  { value: "true_false", label: "Верно/Неверно" },
  { value: "multiple_select", label: "Несколько ответов" },
  { value: "open_ended", label: "Открытый вопрос" },
];

export const TEST_TYPE_LABEL_KEYS: Record<string, MessageKey> = {
  mixed: "value.testTypeMixed",
  multiple_choice: "value.testTypeMultipleChoice",
  true_false: "value.testTypeTrueFalse",
  multiple_select: "value.testTypeMultipleSelect",
  open_ended: "value.testTypeOpenEnded",
};
