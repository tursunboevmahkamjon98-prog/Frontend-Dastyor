/* The language a *document* was generated in is not the same thing as the
 * viewer's own interface language (`useLocale`) — a teacher can browse the
 * dashboard in Russian while every konspekt they generate is in Tajik.
 * `content.language` on a material is always one of these three Cyrillic
 * names (see LANGUAGES in material-types.ts, what the create form sends),
 * so chrome embedded *inside* a document's reading view (section titles,
 * "Answer:", regenerate tooltips) must key off this, not off the UI locale,
 * or a Tajik lesson ends up with Russian headings around Tajik prose.
 *
 * This only covers document viewers (konspekt/test/practical/presentation) —
 * the interactive game HUD (SoloGame/DuelGame/StartScreen/ResultScreen) is
 * app chrome, not a document, and already correctly follows the UI locale
 * via `t()`/`useLocale`.
 */
export type ContentLanguage = "Русский" | "Таджикский" | "Английский";

export function normalizeContentLanguage(language?: string | null): ContentLanguage {
  if (language === "Таджикский" || language === "Английский") return language;
  return "Русский";
}

interface ViewerStrings {
  regenerateQuestion: string;
  regenerateTask: string;
  regenerateSlide: string;
  prevSlide: string;
  nextSlide: string;
  answerLabel: string;
  individualTasks: string;
  groupTasks: string;
  copy: string;
  copied: string;
  closeFullscreen: string;
}

const VIEWER_STRINGS: Record<ContentLanguage, ViewerStrings> = {
  "Русский": {
    regenerateQuestion: "Пересоздать этот вопрос заново",
    regenerateTask: "Пересоздать это задание заново",
    regenerateSlide: "Пересоздать этот слайд заново",
    prevSlide: "Предыдущий слайд",
    nextSlide: "Следующий слайд",
    answerLabel: "Ответ:",
    individualTasks: "Индивидуальные задания",
    groupTasks: "Групповые задания",
    copy: "Копировать",
    copied: "Скопировано",
    closeFullscreen: "Закрыть",
  },
  "Таджикский": {
    regenerateQuestion: "Аз нав эҷод кардани ин савол",
    regenerateTask: "Аз нав эҷод кардани ин супориш",
    regenerateSlide: "Аз нав эҷод кардани ин слайд",
    prevSlide: "Слайди қаблӣ",
    nextSlide: "Слайди навбатӣ",
    answerLabel: "Ҷавоб:",
    individualTasks: "Супоришҳои инфиродӣ",
    groupTasks: "Супоришҳои гурӯҳӣ",
    copy: "Нусха бардоштан",
    copied: "Нусха бардошта шуд",
    closeFullscreen: "Пӯшидан",
  },
  "Английский": {
    regenerateQuestion: "Regenerate this question",
    regenerateTask: "Regenerate this task",
    regenerateSlide: "Regenerate this slide",
    prevSlide: "Previous slide",
    nextSlide: "Next slide",
    answerLabel: "Answer:",
    individualTasks: "Individual tasks",
    groupTasks: "Group tasks",
    copy: "Copy",
    copied: "Copied",
    closeFullscreen: "Close",
  },
};

export function getViewerStrings(language?: string | null): ViewerStrings {
  return VIEWER_STRINGS[normalizeContentLanguage(language)];
}
