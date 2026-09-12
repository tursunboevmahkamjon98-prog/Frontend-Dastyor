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
  amaliy: { label: "Амалӣ супоришҳо", icon: ClipboardList, bg: "bg-amaliy-bg", color: "text-amaliy-icon" },
  igra: { label: "Игра", icon: Gamepad2, bg: "bg-igra-bg", color: "text-igra-icon" },
};

export const MATERIAL_TYPES: MaterialType[] = ["konspekt", "lektsiya", "test", "prezentatsiya", "amaliy", "igra"];

/** The subset a teacher actually browses/keeps as a library — everywhere
 * that lists, counts, or searches "your saved materials" (dashboard/
 * materials, the home stats grid, recent activity) should map over this,
 * not MATERIAL_TYPES. "igra" is excluded on purpose: a game is played in
 * the moment (see components/GamePlayer.tsx), not something a teacher
 * comes back to browse later, so it never appears as a library entry —
 * only as a creation shortcut (quick-create grid, sidebar, the wizard
 * itself all still use MATERIAL_TYPES, unchanged). */
export const LIBRARY_TYPES = MATERIAL_TYPES.filter(
  (t): t is Exclude<MaterialType, "igra"> => t !== "igra"
);

/** Which types the create menu/quick-create grid offer — every type
 * except "igra": the dashboard home's "Сохтани зуд" grid (this export's
 * one call site) is what a teacher scans for "make me a document right
 * now", and a game tile there doesn't belong — it isn't a document, it's
 * played in the moment (see LIBRARY_TYPES' comment above; the wizard at
 * /dashboard/create already excludes it the same way, for the same
 * reason). Kept as its own export rather than switching the call site
 * back to MATERIAL_TYPES directly so a future change is one line again
 * instead of a multi-file hunt. */
export const CREATABLE_TYPES: MaterialType[] = MATERIAL_TYPES.filter(
  (t): t is Exclude<MaterialType, "igra"> => t !== "igra"
);

/** Translation key for each type's display name. MATERIAL_TYPE_CONFIG.label
 * above is a fixed Russian string — fine for the icon/colour lookup it
 * mostly serves, but any name shown to the user should go through this and
 * the `t()` from lib/i18n instead, so the four types are named in the
 * teacher's own language like everything around them. */
export const MATERIAL_TYPE_LABEL_KEY: Record<MaterialType, MessageKey> = {
  konspekt: "type.konspekt",
  lektsiya: "type.lektsiya",
  test: "type.test",
  prezentatsiya: "type.prezentatsiya",
  amaliy: "type.amaliy",
  igra: "type.igra",
};

/** Accusative/object form of each type's name — for "AI создаёт …"-style
 * sentences (see dashboard/create/[type]/page.tsx's loading/error
 * screens), where MATERIAL_TYPE_LABEL_KEY's nominative form reads wrong
 * mid-sentence in Russian ("AI создаёт Презентация"). */
export const MATERIAL_TYPE_LABEL_ACC_KEY: Record<MaterialType, MessageKey> = {
  konspekt: "type.konspektAcc",
  lektsiya: "type.lektsiyaAcc",
  test: "type.testAcc",
  prezentatsiya: "type.prezentatsiyaAcc",
  amaliy: "type.amaliyAcc",
  igra: "type.igraAcc",
};

// Узбекский removed per product decision — backend still handles it fine
// (existing materials generated in it still open/export/download
// correctly, see app/ai_service.py's LANGUAGE_NAMES etc.), it's just no
// longer offered as a choice when creating a new one. Английский stays.
export const LANGUAGES = ["Русский", "Таджикский", "Английский"];
export const LEVELS = ["Лёгкий", "Средний", "Сложный"];

/** The label to SHOW for a stored value.
 *
 * "Русский" and "Средний" are what the backend stores and what the AI
 * prompt expects, so the values must not be translated — but a Tajik
 * teacher choosing a language should not have to read the options in
 * Russian. The value travels, the label is looked up. */
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

// Mirrors the subject keys the backend has dedicated per-subject prompt
// styling for (app/ai_service.py::_SUBJECT_KONSPEKT_PROMPTS) — any other
// value is still accepted, just falls back to a generic style.
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

// Mirrors app/konspekt_templates.py's TEMPLATES registry exactly (same
// ids) — which of these a teacher picks drives BOTH the PDF and DOCX
// export layout for that konspekt (see docx_builder.py's
// _add_konspekt_body / export_builder.py's _add_konspekt_body_pdf /
// cover_builder.py's build_cover_image, all keyed off content.template).
// `mockup` only drives the small CSS preview card in the wizard step
// below — it has no effect on the actual export.
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

/** The four лекция designs, mirroring backend/app/lecture_templates.py.
 *
 * These are not colour variants of one layout: each changes the cover
 * composition, how section headings are set, how a "Важно"/"Пример"
 * callout looks, how a table is ruled and how definitions are presented.
 * `page` below carries exactly those switches so the miniature in the
 * picker shows the document a teacher will actually get. */
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
    /** "playful" only — a single-page grid of pastel ribbon-labelled
     * boxes on ruled notebook paper (see backend/app/konspekt_builder.py's
     * _build_notebook_grid) instead of the usual linear document; the
     * card preview draws a distinct mockup for this rather than reusing
     * the "no cover" run-in-sections one every other cover="none"
     * template shares (see LectureTemplateCard). */
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

/** The six deck designs the presentation wizard offers, mirroring
 * backend/app/export_builder.py's _DECK_THEMES exactly — `header`,
 * `cards`, `badge`, `pastel`/`spiral` and `paper` here are the same
 * switches the PPTX builder reads, so the miniature in the picker shows
 * what the slides will actually look like rather than an illustration of
 * a name. */
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
    /** "playful" only — rotates a 5-colour pastel palette per bullet
     * card instead of one accent colour, and draws a spiral-notebook
     * hole margin down the slide's left edge (see DeckTemplateCard). */
    pastel?: boolean;
  };
}[] = [
  // Listed first, and the backend's default (see export_builder.py's
  // _DECK_THEME_DEFAULT) — built from a real reference photo a teacher
  // sent (a hand-drawn, colourful Canva-style "КОНСПЕКТ" notebook sheet)
  // after every single-accent-colour theme below was tried and rejected
  // ("hunuk" — ugly — every time). True hand-drawn illustration art isn't
  // achievable here (no image-generation capability), but the pastel
  // multi-colour cards, spiral-notebook margin and handwritten-style
  // title font carry the same warm, colourful spirit.
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

// Mirrors app/subject_theme.py's _SUBJECT_ACCENTS exactly (same hexes) —
// used by the presentation web preview (dashboard/materials/[type]/[id])
// to show the same per-subject accent color the actual PPTX/PDF export
// already renders with, instead of one fixed blue regardless of subject.
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

// `label` here is the value shown when no locale is available (kept for
// any caller that hasn't switched to TEST_TYPE_LABEL_KEYS yet) — screens
// that render this list to the user should look up TEST_TYPE_LABEL_KEYS[value]
// via t() instead, same "value travels, the label is looked up" split as
// LANGUAGE_LABEL_KEYS/LEVEL_LABEL_KEYS above.
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
