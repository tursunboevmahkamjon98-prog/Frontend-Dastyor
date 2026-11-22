"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlignCenter,
  AlignLeft,
  AlignRight,
  Bold,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Loader2,
  Maximize2,
  MoreHorizontal,
  Plus,
  Redo2,
  RefreshCw,
  Sigma,
  Strikethrough,
  Trash2,
  X,
  Italic,
  Underline,
  Undo2,
  Menu,
  MessageCircle,
  History,
  Wrench,
  Bookmark,
  GraduationCap,
  SlidersHorizontal,
  CircleHelp,
  Sparkles,
} from "lucide-react";
import { materialsApi, downloadMaterial, ApiError, API_ORIGIN } from "@/lib/api";
import { useLocale, useT } from "@/lib/i18n";
import { KONSPEKT_TEMPLATES, PRESENTATION_TEMPLATES, getSubjectAccent } from "@/lib/material-types";
import { deckTemplateName, templateById, subjectTemplateFor } from "@/lib/subject-templates";
import SubjectTemplatePreview from "@/components/SubjectTemplatePreview";
import PresentMode from "@/components/PresentMode";
import VisualBlockView, { VisualBlock } from "@/components/presentation/SlideVisuals";

interface Slide {
  title: string;
  bullet_points?: string[];
  body?: string;
  speaker_notes?: string;
  visual?: VisualBlock;
  image?: { path: string; caption?: string; credit?: string };
  kind?: string;
  image_query?: string;
  font_size?: number;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strike?: boolean;
  text_align?: "left" | "center" | "right";
}

type PresentationUiLanguage = "tg" | "ru" | "en";

const PRESENTATION_UI: Record<PresentationUiLanguage, {
  back: string;
  saving: string;
  saved: string;
  assistant: string;
  ready: string;
  now: string;
  readyTitle: string;
  improve: string;
  fullscreen: string;
  export: string;
  slide: string;
  slides: string;
  addSlide: string;
  noTitle: string;
  noSlides: string;
  addPoint: string;
  delete: string;
  duplicate: string;
  moveUp: string;
  moveDown: string;
  notes: string;
  titlePlaceholder: string;
  bodyPlaceholder: string;
}> = {
  tg: {
    back: "Бозгашт", saving: "Сабт мешавад…", saved: "Сабт шуд", assistant: "Ёвари AI", ready: "Тайёр", now: "Ҳозир",
    readyTitle: "Презентатсия омода аст", improve: "Такмил додани слайд", fullscreen: "Дар экрани пурра кушодан", export: "Содирот",
    slide: "Слайд", slides: "слайд", addSlide: "Слайди нав", noTitle: "Бе сарлавҳа", noSlides: "Слайд нест", addPoint: "Илова кардани нуқта",
    delete: "Нест кардан", duplicate: "Нусха гирифтан", moveUp: "Ба боло бурдан", moveDown: "Ба поён бурдан", notes: "Эзоҳҳо",
    titlePlaceholder: "Сарлавҳаи слайд", bodyPlaceholder: "Матни кӯтоҳи слайд",
  },
  ru: {
    back: "Назад", saving: "Сохранение…", saved: "Сохранено", assistant: "AI-помощник", ready: "Готово", now: "Только что",
    readyTitle: "Презентация готова", improve: "Улучшить слайд", fullscreen: "Открыть на весь экран", export: "Экспорт",
    slide: "Слайд", slides: "слайдов", addSlide: "Новый слайд", noTitle: "Без заголовка", noSlides: "Нет слайдов", addPoint: "Добавить пункт",
    delete: "Удалить", duplicate: "Дублировать", moveUp: "Переместить вверх", moveDown: "Переместить вниз", notes: "Заметки",
    titlePlaceholder: "Заголовок слайда", bodyPlaceholder: "Короткий текст слайда",
  },
  en: {
    back: "Back", saving: "Saving…", saved: "Saved", assistant: "AI assistant", ready: "Ready", now: "Just now",
    readyTitle: "Presentation ready", improve: "Improve slide", fullscreen: "Open full screen", export: "Export",
    slide: "Slide", slides: "slides", addSlide: "New slide", noTitle: "Untitled", noSlides: "No slides", addPoint: "Add point",
    delete: "Delete", duplicate: "Duplicate", moveUp: "Move up", moveDown: "Move down", notes: "Notes",
    titlePlaceholder: "Slide title", bodyPlaceholder: "Short slide text",
  },
};

void PRESENTATION_UI;

const SLIDE_LAYOUT_OPTIONS = [
  { id: "title", label: "Title" },
  { id: "section", label: "Section Header" },
  { id: "title-body", label: "Title + Body" },
  { id: "text-image", label: "Text + Image" },
  { id: "image-text", label: "Image + Text" },
  { id: "two-column", label: "2 Column" },
  { id: "three-column", label: "3 Column" },
] as const;

const PRESENTATION_UI_SAFE: Record<PresentationUiLanguage, typeof PRESENTATION_UI.tg> = {
  tg: {
    back: "\u0411\u043e\u0437\u0433\u0430\u0448\u0442", saving: "\u0417\u0430\u0445\u0438\u0440\u0430 \u0448\u0443\u0434\u0430 \u0438\u0441\u0442\u043e\u0434\u0430\u0430\u0441\u0442\u2026", saved: "\u0417\u0430\u0445\u0438\u0440\u0430 \u0448\u0443\u0434", assistant: "\u0401\u0432\u0430\u0440\u0438 AI", ready: "\u0422\u0430\u0439\u0451\u0440", now: "\u04b2\u043e\u0437\u0438\u0440",
    readyTitle: "\u041f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0442\u0441\u0438\u044f \u043e\u043c\u043e\u0434\u0430 \u0430\u0441\u0442", improve: "\u0422\u0430\u043a\u043c\u0438\u043b \u0434\u043e\u0434\u0430\u043d\u0438 \u0441\u043b\u0430\u0439\u0434", fullscreen: "\u0414\u0430\u0440 \u044d\u043a\u0440\u0430\u043d\u0438 \u043f\u0443\u0440\u0440\u0430 \u043a\u0443\u0448\u043e\u0434\u0430\u043d", export: "\u0421\u043e\u0434\u0438\u0440\u043e\u0442",
    slide: "\u0421\u043b\u0430\u0439\u0434", slides: "\u0441\u043b\u0430\u0439\u0434", addSlide: "\u0421\u043b\u0430\u0439\u0434\u0438 \u043d\u0430\u0432", noTitle: "\u0411\u0435 \u0441\u0430\u0440\u043b\u0430\u0432\u04b3\u0430", noSlides: "\u0421\u043b\u0430\u0439\u0434 \u043d\u0435\u0441\u0442", addPoint: "\u0411\u0430\u043d\u0434 \u0438\u043b\u043e\u0432\u0430 \u043a\u0430\u0440\u0434\u0430\u043d",
    delete: "\u041d\u0435\u0441\u0442 \u043a\u0430\u0440\u0434\u0430\u043d", duplicate: "\u041d\u0443\u0441\u0445\u0430 \u0433\u0438\u0440\u0438\u0444\u0442\u0430\u043d", moveUp: "\u0411\u0430 \u0431\u043e\u043b\u043e \u0431\u0443\u0440\u0434\u0430\u043d", moveDown: "\u0411\u0430 \u043f\u043e\u0451\u043d \u0431\u0443\u0440\u0434\u0430\u043d", notes: "\u042d\u0437\u043e\u04b3\u04b3\u043e \u0431\u0430\u0440\u043e\u0438 \u043e\u043c\u04ef\u0437\u0433\u043e\u0440",
    titlePlaceholder: "\u0421\u0430\u0440\u043b\u0430\u0432\u04b3\u0430\u0438 \u0441\u043b\u0430\u0439\u0434", bodyPlaceholder: "\u041c\u0430\u0442\u043d\u0438 \u043a\u04ef\u0442\u043e\u04b3\u0438 \u0441\u043b\u0430\u0439\u0434",
  },
  ru: {
    back: "\u041d\u0430\u0437\u0430\u0434", saving: "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435\u2026", saved: "\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e", assistant: "AI-\u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a", ready: "\u0413\u043e\u0442\u043e\u0432\u043e", now: "\u0422\u043e\u043b\u044c\u043a\u043e \u0447\u0442\u043e",
    readyTitle: "\u041f\u0440\u0435\u0437\u0435\u043d\u0442\u0430\u0446\u0438\u044f \u0433\u043e\u0442\u043e\u0432\u0430", improve: "\u0423\u043b\u0443\u0447\u0448\u0438\u0442\u044c \u0441\u043b\u0430\u0439\u0434", fullscreen: "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043d\u0430 \u0432\u0435\u0441\u044c \u044d\u043a\u0440\u0430\u043d", export: "\u042d\u043a\u0441\u043f\u043e\u0440\u0442",
    slide: "\u0421\u043b\u0430\u0439\u0434", slides: "\u0441\u043b\u0430\u0439\u0434\u043e\u0432", addSlide: "\u041d\u043e\u0432\u044b\u0439 \u0441\u043b\u0430\u0439\u0434", noTitle: "\u0411\u0435\u0437 \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043a\u0430", noSlides: "\u041d\u0435\u0442 \u0441\u043b\u0430\u0439\u0434\u043e\u0432", addPoint: "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u0443\u043d\u043a\u0442",
    delete: "\u0423\u0434\u0430\u043b\u0438\u0442\u044c", duplicate: "\u0414\u0443\u0431\u043b\u0438\u0440\u043e\u0432\u0430\u0442\u044c", moveUp: "\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432\u0432\u0435\u0440\u0445", moveDown: "\u041f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c \u0432\u043d\u0438\u0437", notes: "\u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u0443\u0447\u0438\u0442\u0435\u043b\u044f",
    titlePlaceholder: "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a \u0441\u043b\u0430\u0439\u0434\u0430", bodyPlaceholder: "\u041a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442 \u0441\u043b\u0430\u0439\u0434\u0430",
  },
  en: {
    back: "Back", saving: "Saving\u2026", saved: "Saved", assistant: "AI assistant", ready: "Ready", now: "Just now",
    readyTitle: "Presentation ready", improve: "Improve slide", fullscreen: "Open full screen", export: "Export",
    slide: "Slide", slides: "slides", addSlide: "New slide", noTitle: "Untitled", noSlides: "No slides", addPoint: "Add point",
    delete: "Delete", duplicate: "Duplicate", moveUp: "Move up", moveDown: "Move down", notes: "Teacher notes",
    titlePlaceholder: "Slide title", bodyPlaceholder: "Short slide text",
  },
};

const SLIDE_LAYOUT_LABELS: Record<PresentationUiLanguage, Record<(typeof SLIDE_LAYOUT_OPTIONS)[number]["id"], string>> = {
  tg: {
    title: "\u0421\u0430\u0440\u043b\u0430\u0432\u04b3\u0430", section: "\u0421\u0430\u0440\u043b\u0430\u0432\u04b3\u0430\u0438 \u049b\u0438\u0441\u043c", "title-body": "\u0421\u0430\u0440\u043b\u0430\u0432\u04b3\u0430 + \u043c\u0430\u0442\u043d", "text-image": "\u041c\u0430\u0442\u043d + \u0440\u0430\u0441\u043c", "image-text": "\u0420\u0430\u0441\u043c + \u043c\u0430\u0442\u043d", "two-column": "2 \u0441\u0443\u0442\u0443\u043d", "three-column": "3 \u0441\u0443\u0442\u0443\u043d",
  },
  ru: {
    title: "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a", section: "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a \u0440\u0430\u0437\u0434\u0435\u043b\u0430", "title-body": "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a + \u0442\u0435\u043a\u0441\u0442", "text-image": "\u0422\u0435\u043a\u0441\u0442 + \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435", "image-text": "\u0418\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435 + \u0442\u0435\u043a\u0441\u0442", "two-column": "2 \u043a\u043e\u043b\u043e\u043d\u043a\u0438", "three-column": "3 \u043a\u043e\u043b\u043e\u043d\u043a\u0438",
  },
  en: {
    title: "Title", section: "Section Header", "title-body": "Title + Body", "text-image": "Text + Image", "image-text": "Image + Text", "two-column": "2 Column", "three-column": "3 Column",
  },
};

const FORMAT_LABELS: Record<PresentationUiLanguage, { heading1: string; heading2: string; body: string }> = {
  tg: { heading1: `${PRESENTATION_UI_SAFE.tg.titlePlaceholder} 1`, heading2: `${PRESENTATION_UI_SAFE.tg.titlePlaceholder} 2`, body: PRESENTATION_UI_SAFE.tg.bodyPlaceholder },
  ru: { heading1: `${PRESENTATION_UI_SAFE.ru.titlePlaceholder} 1`, heading2: `${PRESENTATION_UI_SAFE.ru.titlePlaceholder} 2`, body: PRESENTATION_UI_SAFE.ru.bodyPlaceholder },
  en: { heading1: "Heading 1", heading2: "Heading 2", body: "Body" },
};

function presentationUiLanguage(language: unknown): PresentationUiLanguage {
  const value = String(language ?? "").toLowerCase();
  if (value.includes("тадж") || value.includes("tajik") || value.includes("тоҷик") || value.includes("тоҷикӣ")) return "tg";
  if (value.includes("рус") || value.includes("russian")) return "ru";
  return "en";
}








export default function PresentationEditorPage() {
  const t = useT();
  const { locale } = useLocale();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [item, setItem] = useState<{ title: string; subject: string; grade: string } | null>(null);
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [selected, setSelected] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [regenerating, setRegenerating] = useState(false);
  const [addingSlide, setAddingSlide] = useState(false);
  const [presenting, setPresenting] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    materialsApi
      .get("prezentatsiya", id)
      .then((loaded) => {
        setItem({ title: loaded.title, subject: loaded.subject, grade: loaded.grade });
        try {
          setContent(JSON.parse(loaded.slides_json ?? "{}"));
        } catch {
          setContent({});
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : t("material.loadFailed")));
  }, [id]);

  const slides = (content.slides as Slide[] | undefined) ?? [];
  const accent = getSubjectAccent(content.subject as string | undefined);
  const ui = PRESENTATION_UI_SAFE[locale || presentationUiLanguage(content.language)];
  const layoutLabels = SLIDE_LAYOUT_LABELS[locale || presentationUiLanguage(content.language)];
  const formatLabels = FORMAT_LABELS[locale || presentationUiLanguage(content.language)];
  
  
  
  
  const deckDesignName = deckTemplateName(content.template as string | undefined);
  const deckDesign = templateById(content.template as string | undefined)
    ?? (PRESENTATION_TEMPLATES.some((t) => t.id === content.template)
        ? undefined                      
        : subjectTemplateFor(content.subject as string | undefined));

  
  
  
  
  
  const legacyTmpl = PRESENTATION_TEMPLATES.find((t) => t.id === content.template);
  const tmpl = legacyTmpl ?? {
    ...PRESENTATION_TEMPLATES[0],
    name: deckDesignName,
    deck: {
      ...PRESENTATION_TEMPLATES[0].deck,
      paper: deckDesign?.bg ?? "#ffffff",
      ink: deckDesign?.ink ?? "#1e2937",
      header:
        deckDesign?.header === "band" ? "band" as const
        : deckDesign?.header === "underline" || deckDesign?.header === "prompt"
          || deckDesign?.header === "measure" ? "underline" as const
        : deckDesign?.header === "smallcaps" ? "plain" as const
        : "rule" as const,
      cards: deckDesign?.card !== "quote",
      badge: true,
      pastel: deckDesign?.card === "pastel",
      serif: Boolean(deckDesign?.serif),
      caps: deckDesign?.header === "smallcaps",
    },
  };
  const presentTmpl = KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0];

  
  
  
  
  
  
  
  function persist(next: Record<string, unknown>) {
    setContent(next);
    setSaveState("saving");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        await materialsApi.update("prezentatsiya", id, { slides_json: JSON.stringify(next) });
        setSaveState("saved");
      } catch {
        setSaveState("idle");
      }
    }, 800);
  }

  function updateSlides(nextSlides: Slide[]) {
    persist({ ...content, slides: nextSlides });
  }

  function updateSlide(index: number, patch: Partial<Slide>) {
    updateSlides(slides.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  function moveSlide(index: number, dir: -1 | 1) {
    const target = index + dir;
    if (target < 0 || target >= slides.length) return;
    const next = [...slides];
    [next[index], next[target]] = [next[target], next[index]];
    updateSlides(next);
    setSelected(target);
  }

  function deleteSlide(index: number) {
    if (slides.length <= 1) return;
    if (!confirm(`${ui.delete}?`)) return;
    const next = slides.filter((_, i) => i !== index);
    updateSlides(next);
    setSelected((s) => Math.min(s, next.length - 1));
  }

  function duplicateSlide(index: number) {
    const clone: Slide = JSON.parse(JSON.stringify(slides[index]));
    const next = [...slides.slice(0, index + 1), clone, ...slides.slice(index + 1)];
    updateSlides(next);
    setSelected(index + 1);
  }

  
  
  
  
  
  
  async function regenerateAt(index: number, replace: boolean) {
    if (!item) return;
    if (replace) setRegenerating(true);
    else setAddingSlide(true);
    try {
      const result = await materialsApi.regeneratePresentationSlide({
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        item_index: index,
        existing_items: slides as unknown as Record<string, unknown>[],
      });
      const nextSlide = result.item as unknown as Slide;
      if (replace) {
        updateSlide(index, nextSlide);
      } else {
        const next = [...slides, nextSlide];
        updateSlides(next);
        setSelected(next.length - 1);
      }
    } catch {
      
    } finally {
      if (replace) setRegenerating(false);
      else setAddingSlide(false);
    }
  }

  async function handleDownload(format: "pptx" | "pdf") {
    setDownloading(format);
    try {
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(format, { material_type: "prezentatsiya", content, language });
    } catch {
      
    } finally {
      setDownloading(null);
    }
  }

  function closeEditor() {
    if (typeof window !== "undefined" && document.referrer.startsWith(window.location.origin)) {
      router.back();
      return;
    }
    router.push("/dashboard");
  }

  if (error) {
    return <div className="px-4 pt-10 text-center text-sm text-primary-dark">{error}</div>;
  }
  if (!item) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">{t("material.loading")}</div>;
  }

  const s = slides[selected];

  return (
    <div className="presentation-editor-shell flex h-[calc(100dvh-4rem)] flex-col lg:h-dvh">
      {}
      <div className="presentation-editor-topbar flex shrink-0 items-center justify-between border-b border-border-light bg-surface px-4 py-3">
        <h1 className="presentation-editor-topbar__title truncate">{item.title}</h1>
        <div className="presentation-editor-topbar__actions flex shrink-0 items-center gap-2 text-xs text-text-tertiary">
          {saveState === "saving" && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> {ui.saving}
            </span>
          )}
          {saveState === "saved" && <span>{ui.saved}</span>}
          <button type="button" className="presentation-editor-topbar__icon" aria-label="Bookmark">
            <Bookmark className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => handleDownload("pptx")} disabled={downloading !== null} className="presentation-editor-topbar__export">
            {downloading === "pptx" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            {ui.export}
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
          <button type="button" onClick={closeEditor} className="presentation-editor-topbar__icon" aria-label={t("common.close")}>
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="presentation-editor-formatbar" aria-label="Formatting toolbar">
        <button type="button" className="presentation-editor-formatbar__icon" disabled aria-label="Undo"><Undo2 className="h-4 w-4" /></button>
        <button type="button" className="presentation-editor-formatbar__icon" disabled aria-label="Redo"><Redo2 className="h-4 w-4" /></button>
        <span className="presentation-editor-formatbar__divider" />
        <select
          aria-label="Text style"
          value={(s?.font_size ?? 32) <= 20 ? "body" : (s?.font_size ?? 32) <= 28 ? "heading2" : "heading1"}
          onChange={(e) => {
            if (!s) return;
            const next = e.target.value === "body"
              ? { font_size: 18, bold: false }
              : e.target.value === "heading2"
                ? { font_size: 26, bold: true }
                : { font_size: 32, bold: true };
            updateSlide(selected, next);
          }}
          className="presentation-editor-formatbar__select presentation-editor-formatbar__select--style"
        >
          <option value="heading1">{formatLabels.heading1}</option>
          <option value="heading2">{formatLabels.heading2}</option>
          <option value="body">{formatLabels.body}</option>
        </select>
        <span className="presentation-editor-formatbar__divider" />
        <span className="presentation-editor-formatbar__font">Arial</span>
        <button type="button" className="presentation-editor-formatbar__icon" disabled={!s} onClick={() => s && updateSlide(selected, { font_size: Math.max(18, (s.font_size ?? 32) - 2) })} aria-label="Decrease font size"><span className="text-lg">−</span></button>
        <input
          aria-label="Font size"
          type="number"
          min={16}
          max={96}
          value={Math.min(s?.font_size ?? 32, 34)}
          onChange={(e) => s && updateSlide(selected, { font_size: Math.max(16, Math.min(96, Number(e.target.value) || 44)) })}
          className="presentation-editor-formatbar__size"
        />
        <button type="button" className="presentation-editor-formatbar__icon" disabled={!s} onClick={() => s && updateSlide(selected, { font_size: Math.min(72, (s.font_size ?? 32) + 2) })} aria-label="Increase font size"><Plus className="h-4 w-4" /></button>
        <span className="presentation-editor-formatbar__divider" />
        <button type="button" className={`presentation-editor-formatbar__icon ${s?.bold !== false ? "is-active" : ""}`} disabled={!s} onClick={() => s && updateSlide(selected, { bold: s.bold === false })} aria-label="Bold"><Bold className="h-4 w-4" /></button>
        <button type="button" className={`presentation-editor-formatbar__icon ${s?.italic ? "is-active" : ""}`} disabled={!s} onClick={() => s && updateSlide(selected, { italic: !s.italic })} aria-label="Italic"><Italic className="h-4 w-4" /></button>
        <button type="button" className={`presentation-editor-formatbar__icon ${s?.underline ? "is-active" : ""}`} disabled={!s} onClick={() => s && updateSlide(selected, { underline: !s.underline })} aria-label="Underline"><Underline className="h-4 w-4" /></button>
        <button type="button" className={`presentation-editor-formatbar__icon ${s?.strike ? "is-active" : ""}`} disabled={!s} onClick={() => s && updateSlide(selected, { strike: !s.strike })} aria-label="Strikethrough"><Strikethrough className="h-4 w-4" /></button>
        <button type="button" className="presentation-editor-formatbar__icon" disabled aria-label="More formatting"><MoreHorizontal className="h-4 w-4" /></button>
        <span className="presentation-editor-formatbar__divider" />
        <button type="button" className="presentation-editor-formatbar__icon" disabled aria-label="Insert formula"><Sigma className="h-4 w-4" /></button>
        <button type="button" className={`presentation-editor-formatbar__icon ${s?.text_align === "center" ? "is-active" : ""}`} disabled={!s} onClick={() => s && updateSlide(selected, { text_align: s.text_align === "left" || !s.text_align ? "center" : s.text_align === "center" ? "right" : "left" })} aria-label="Text alignment">
          {s?.text_align === "right" ? <AlignRight className="h-4 w-4" /> : s?.text_align === "center" ? <AlignCenter className="h-4 w-4" /> : <AlignLeft className="h-4 w-4" />}
        </button>
      </div>

      <div className="presentation-editor-layout flex min-h-0 flex-1 flex-col lg:grid">
        <aside className="presentation-editor-rail hidden" aria-label="Presentation navigation">
          <button
            type="button"
            onClick={closeEditor}
            className="presentation-editor-rail__back"
            aria-label={ui.back}
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="presentation-editor-rail__icons" aria-hidden="true">
            <Menu />
            <MessageCircle />
            <Wrench />
            <History />
            <Bookmark />
            <GraduationCap />
            <SlidersHorizontal />
          </div>
          <CircleHelp className="presentation-editor-rail__help" aria-hidden="true" />
        </aside>

        {}
        <div className="presentation-editor-chat hidden flex min-h-0 shrink-0 gap-2 overflow-x-auto border-b border-border-light bg-surface-muted p-3 lg:h-full lg:flex-col lg:overflow-y-auto lg:overflow-x-hidden lg:border-b-0 lg:border-r">
          <div className="presentation-editor-chat__heading">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-violet-400" />
              <span>{ui.assistant}</span>
            </div>
            <span className="presentation-editor-chat__muted">{saveState === "saving" ? ui.saving : ui.ready}</span>
          </div>
          <div className="presentation-editor-chat__prompt">{item.title}</div>
          <div className="presentation-editor-chat__meta">{ui.now}</div>
          <div className="presentation-editor-chat__result">
            <p className="font-semibold">{ui.readyTitle}</p>
            <p>{slides.length} {ui.slides} · {s?.title || ui.slide}</p>
          </div>
          <div className="presentation-editor-chat__actions">
            <button
              onClick={() => regenerateAt(selected, true)}
              disabled={regenerating || !s}
              className="presentation-editor-chat__primary"
            >
              {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {ui.improve}
            </button>
            <button
              onClick={() => setPresenting(true)}
              disabled={slides.length === 0}
              className="presentation-editor-chat__secondary"
            >
              <Maximize2 className="h-4 w-4" />
              {ui.fullscreen}
            </button>
            <div className="flex gap-2">
              {(["pptx", "pdf"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => handleDownload(f)}
                  disabled={downloading !== null}
                  className="presentation-editor-chat__download"
                >
                  {downloading === f ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                  .{f}
                </button>
              ))}
            </div>
          </div>
          {slides.map((slide, i) => (
            <div
              key={i}
              onClick={() => setSelected(i)}
              className={`presentation-editor-slide-thumb group relative shrink-0 cursor-pointer rounded-lg border p-1.5 lg:shrink transition ${
                i === selected ? "border-primary ring-2 ring-primary/20" : "border-border hover:border-border-strong"
              }`}
              style={{ width: "clamp(104px, 30vw, 150px)" }}
            >
              <div
                className="overflow-hidden rounded"
                style={{ aspectRatio: "16 / 9", backgroundColor: tmpl.deck.paper }}
              >
                <div className="px-1.5 pt-1" style={tmpl.deck.header === "band" ? { backgroundColor: accent, paddingBottom: 3 } : undefined}>
                  <p
                    className="line-clamp-2 text-[7px] font-bold leading-tight"
                    style={{ color: tmpl.deck.header === "band" ? "#fff" : tmpl.deck.ink }}
                  >
                    {i + 1}. {slide.title || ui.noTitle}
                  </p>
                </div>
              </div>
              {}
              <div className="absolute -top-1.5 -right-1.5 flex gap-0.5 [@media(hover:hover)]:hidden [@media(hover:hover)]:group-hover:flex">
                <button
                    title={ui.moveUp}
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSlide(i, -1);
                  }}
                  disabled={i === 0}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-surface text-text-secondary shadow disabled:opacity-30 [@media(hover:hover)]:h-5 [@media(hover:hover)]:w-5"
                >
                  <ChevronUp className="h-3.5 w-3.5 [@media(hover:hover)]:h-3 [@media(hover:hover)]:w-3" />
                </button>
                <button
                    title={ui.moveDown}
                  onClick={(e) => {
                    e.stopPropagation();
                    moveSlide(i, 1);
                  }}
                  disabled={i === slides.length - 1}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-surface text-text-secondary shadow disabled:opacity-30 [@media(hover:hover)]:h-5 [@media(hover:hover)]:w-5"
                >
                  <ChevronDown className="h-3.5 w-3.5 [@media(hover:hover)]:h-3 [@media(hover:hover)]:w-3" />
                </button>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-text-tertiary">{i + 1}</span>
                <div className="flex gap-1">
                  <button
                    title={ui.duplicate}
                    onClick={(e) => {
                      e.stopPropagation();
                      duplicateSlide(i);
                    }}
                    className="text-text-tertiary hover:text-text-primary"
                  >
                    <Copy className="h-3 w-3" />
                  </button>
                  <button
                    title={ui.delete}
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteSlide(i);
                    }}
                    disabled={slides.length <= 1}
                    className="text-text-tertiary hover:text-primary-dark disabled:opacity-30"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          <button
            onClick={() => regenerateAt(slides.length, false)}
            disabled={addingSlide}
            className="flex shrink-0 items-center justify-center gap-1.5 rounded-lg border border-dashed border-border-strong px-3 py-2 text-xs font-medium text-text-secondary hover:border-primary hover:text-primary disabled:opacity-60 lg:w-full"
            style={{ minWidth: 110 }}
          >
            {addingSlide ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            {ui.addSlide}
          </button>
        </div>

        {}
        <div className="presentation-editor-canvas min-h-0 flex-1 overflow-y-auto p-4 lg:p-8">
          <div className="presentation-editor-canvas__toolbar">
            <div className="flex min-w-0 items-center gap-3">
              <span className="presentation-editor-canvas__title">{item.title}</span>
              <span className="presentation-editor-canvas__theme">{deckDesignName}</span>
              <span className="presentation-editor-canvas__counter">{ui.slide} {selected + 1}/{slides.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => handleDownload("pptx")} disabled={downloading !== null} className="presentation-editor-canvas__export">
                {downloading === "pptx" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                {ui.export}
              </button>
              <button type="button" onClick={closeEditor} className="presentation-editor-canvas__close" aria-label={t("common.close")}>
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
          <div className="presentation-editor-layout-tools" aria-label="Slide layout">
            {SLIDE_LAYOUT_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => s && updateSlide(selected, { kind: option.id })}
                className={`presentation-editor-layout-tool ${s?.kind === option.id ? "is-active" : ""}`}
              >
                <span className="presentation-editor-layout-tool__icon" aria-hidden="true" />
                {layoutLabels[option.id]}
              </button>
            ))}
          </div>
          <p className="presentation-editor-slide-label">{ui.slide} {selected + 1}/{slides.length}</p>
          {s ? (
            <div
              className={`presentation-editor-slide relative mx-auto flex aspect-video w-full max-w-6xl flex-col overflow-hidden rounded-xl border bg-white shadow-[0_20px_60px_-32px_rgba(15,23,42,0.45)] ${s.image ? "presentation-editor-slide--image" : ""}`}
              style={{ borderColor: `${accent}55`, background: s.image ? "#111827" : tmpl.deck.paper }}
            >
              {s.image && <img className="presentation-editor-slide__image" src={`${API_ORIGIN}${s.image.path}`} alt={s.image.caption ?? ""} />}
              {s.image && <div className="presentation-editor-slide__scrim" />}
              <div className="presentation-editor-slide__content relative flex min-h-0 flex-1 flex-col" style={{ textAlign: s.text_align ?? "left" }}>
                <div className="presentation-editor-slide__body-content min-h-0 flex-1 space-y-3 overflow-y-auto p-5 pt-4 sm:p-10 sm:pt-8">
                  {}
                  <input
                    value={s.title}
                    onChange={(e) => updateSlide(selected, { title: e.target.value })}
                    placeholder={ui.titlePlaceholder}
                    className="presentation-editor-slide__title w-full rounded-lg border border-transparent bg-white/60 px-2 py-1 text-sm font-semibold text-text-primary outline-none focus:border-primary/40 focus:bg-white"
                    style={{ fontSize: `${Math.min(s.font_size ?? 32, 40)}px`, fontWeight: s.bold === false ? 500 : 800, fontStyle: s.italic ? "italic" : "normal", textDecoration: `${s.underline ? "underline " : ""}${s.strike ? "line-through" : ""}`.trim() || "none" }}
                  />

                  {}
                  <div className="presentation-editor-slide__bullets space-y-1.5">
                    {(s.bullet_points ?? []).map((b, j) => (
                      <div key={j} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: accent }} aria-hidden />
                        <input
                          value={b}
                          onChange={(e) => {
                            const next = [...(s.bullet_points ?? [])];
                            next[j] = e.target.value;
                            updateSlide(selected, { bullet_points: next });
                          }}
                          className="presentation-editor-slide__bullet min-w-0 flex-1 rounded-lg border border-transparent bg-white/50 px-2 py-1 text-sm text-text-primary outline-none focus:border-primary/40 focus:bg-white"
                        />
                        <button
                          onClick={() => {
                            const next = (s.bullet_points ?? []).filter((_, k) => k !== j);
                            updateSlide(selected, { bullet_points: next });
                          }}
                          className="shrink-0 text-text-tertiary hover:text-primary-dark"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => updateSlide(selected, { bullet_points: [...(s.bullet_points ?? []), ""] })}
                      className="flex items-center gap-1 text-xs font-medium text-text-tertiary hover:text-primary"
                    >
                      <Plus className="h-3 w-3" /> {ui.addPoint}
                    </button>
                  </div>

                  {s.visual && <VisualBlockView visual={s.visual} accent={accent} />}

                  {s.image && (
                    <div className="presentation-editor-slide__image-action relative">
                      <button
                        onClick={() => {
                          const { image: _drop, ...rest } = s;
                          void _drop;
                          updateSlides(slides.map((sl, i) => (i === selected ? (rest as Slide) : sl)));
                        }}
                        className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-black/50 text-white hover:bg-black/70"
                        title={t("material.deleteConfirm")}
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}

                  {}
                  <textarea
                    value={s.body ?? ""}
                    onChange={(e) => updateSlide(selected, { body: e.target.value })}
                    placeholder={ui.bodyPlaceholder}
                    rows={2}
                    className="presentation-editor-slide__body w-full resize-none rounded-lg border border-transparent bg-white/50 px-2 py-1.5 text-xs text-text-secondary outline-none focus:border-primary/40 focus:bg-white"
                  />

                  {}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-center text-sm text-text-secondary">{t("material.noSlides")}</p>
          )}
          {s && (
            <details className="presentation-editor-speaker-notes">
              <summary>{ui.notes}</summary>
              <textarea
                value={s.speaker_notes ?? ""}
                onChange={(e) => updateSlide(selected, { speaker_notes: e.target.value })}
                rows={4}
                className="presentation-editor-speaker-notes__input"
              />
            </details>
          )}
          <div className="presentation-editor-slide-stack">
            {slides.map((slide, index) => index === selected ? null : (
              <article key={index} className="presentation-editor-preview" onClick={() => setSelected(index)}>
                <p className="presentation-editor-preview__counter">{ui.slide} {index + 1}/{slides.length}</p>
                <div className="presentation-editor-preview__page" style={{ borderColor: `${accent}55`, background: tmpl.deck.paper }}>
                  {slide.image && <img className="presentation-editor-preview__image" src={`${API_ORIGIN}${slide.image.path}`} alt={slide.image.caption ?? ""} />}
                  {slide.image && <div className="presentation-editor-preview__scrim" />}
                  <div className={`presentation-editor-preview__body ${slide.image ? "presentation-editor-preview__body--image" : ""}`}>
                    <h2>{slide.title || ui.noTitle}</h2>
                    {(slide.bullet_points?.length ?? 0) > 0 && (
                      <ul>
                        {(slide.bullet_points ?? []).map((point, pointIndex) => (
                          <li key={pointIndex}>
                            <span style={{ backgroundColor: accent }} aria-hidden="true" />
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {slide.body && <p>{slide.body}</p>}
                    {slide.visual && <VisualBlockView visual={slide.visual} accent={accent} />}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>

        {}
        <div className="presentation-editor-inspector shrink-0 space-y-4 border-t border-border-light bg-surface p-4 lg:h-full lg:w-[300px] lg:overflow-y-auto lg:border-l lg:border-t-0">
          <button
            onClick={() => regenerateAt(selected, true)}
            disabled={regenerating || !s}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:bg-primary-dark disabled:opacity-60"
          >
            {regenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {t("material.regenSlide")}
          </button>

          <button
            onClick={() => setPresenting(true)}
            disabled={slides.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface-muted py-2.5 text-sm font-semibold text-text-primary transition hover:bg-surface disabled:opacity-60"
          >
            <Maximize2 className="h-4 w-4" />
            {t("material.openFull")}
          </button>

          {}
          <div className="rounded-xl border border-border bg-surface p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
              {t("material.design")}
            </p>
            {deckDesign && <SubjectTemplatePreview template={deckDesign} className="mb-2" />}
            <p className="text-sm font-medium text-text-primary">{deckDesignName}</p>
            {deckDesign && (
              <p className="mt-0.5 text-xs leading-snug text-text-tertiary">{deckDesign.note}</p>
            )}
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-tertiary">{t("material.downloadSection")}</p>
            <div className="flex gap-2">
              {(["pptx", "pdf"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => handleDownload(f)}
                  disabled={downloading !== null}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted disabled:opacity-60"
                >
                  {downloading === f ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  .{f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {presenting && (
        <PresentMode
          slides={slides}
          accent={accent}
          template={presentTmpl}
          initialIndex={selected}
          onClose={() => setPresenting(false)}
        />
      )}
    </div>
  );
}
