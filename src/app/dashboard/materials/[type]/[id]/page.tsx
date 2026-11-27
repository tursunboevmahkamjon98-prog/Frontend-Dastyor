"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Bookmark, Copy, Download, Trash2, Loader2, RefreshCw, Pencil, Play, Send, Sparkles, X, Undo2, Redo2, Bold, Italic, Underline, Strikethrough, MoreHorizontal, Sigma, AlignLeft, Printer, Table2 } from "lucide-react";
import { materialsApi, downloadMaterial, MaterialOut, MaterialType, ApiError } from "@/lib/api";
import PdfPreview from "@/components/PdfPreview";
import { useT } from "@/lib/i18n";
import { MATERIAL_TYPE_CONFIG, KONSPEKT_TEMPLATES, getSubjectAccent } from "@/lib/material-types";
import GamePlayer from "@/components/GamePlayer";
import PresentMode from "@/components/PresentMode";
import VisualBlockView, { VisualBlock, SlideHeader } from "@/components/presentation/SlideVisuals";
import DocumentEditor from "@/components/DocumentEditor";
import MathText from "@/components/konspekt/MathText";

interface Question {
  question: string;
  type?: string;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
}

interface PracticalTask {
  title?: string;
  difficulty?: string;
  instructions?: string;
  expected_outcome?: string;
  group_size?: string;
  roles?: string[];
}

interface Slide {
  title: string;
  bullet_points?: string[];
  speaker_notes?: string;
  visual?: VisualBlock;
}

function quickEditOptions(language: string): string[] {
  if (language === "Таджикский") {
    return [
      "Матнро содатар кунед",
      "Кори гурӯҳӣ илова кунед",
      "Марҳилаҳои дарс ва вақтро санҷед",
      "Мисолҳои иловагӣ илова кунед",
    ];
  }
  if (language === "Английский") {
    return [
      "Simplify the language",
      "Add a group activity",
      "Review stages and timing",
      "Add two relevant examples",
    ];
  }
  return [
    "Упростите язык",
    "Добавьте групповую работу",
    "Проверьте этапы и время",
    "Добавьте два подходящих примера",
  ];
}




const CONTENT_FIELD: Record<MaterialType, "content" | "slides_json" | "questions_json" | "tasks_json" | "game_json"> = {
  konspekt: "content",
  lektsiya: "content",
  prezentatsiya: "slides_json",
  test: "questions_json",
  amaliy: "tasks_json",
  igra: "game_json",
};

export default function MaterialViewerPage() {
  const t = useT();
  const params = useParams<{ type: string; id: string }>();
  const router = useRouter();
  const type = params.type as MaterialType;
  const id = params.id;
  const config = MATERIAL_TYPE_CONFIG[type];

  const [item, setItem] = useState<MaterialOut | null>(null);
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [regeneratingSlide, setRegeneratingSlide] = useState<number | null>(null);
  const [presenting, setPresenting] = useState(false);
  
  
  
  
  
  
  
  const [chatInstruction, setChatInstruction] = useState("");
  const [chatSubmitting, setChatSubmitting] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  useEffect(() => {
    if (String(type) === "prezentatsiya") {
      router.replace(`/dashboard/presentations/${id}/edit`);
      return;
    }
    materialsApi
      .get(type, id)
      .then((loaded) => {
        setItem(loaded);
        const raw = loaded.content ?? loaded.questions_json ?? loaded.slides_json ?? loaded.tasks_json ?? loaded.game_json ?? "{}";
        try {
          setContent(JSON.parse(raw));
        } catch {
          setContent({});
        }
      })
      // "" means "no server message": the translated fallback is chosen at render time.
      .catch((err) => setError(err instanceof ApiError ? err.message : ""));
  }, [type, id, router]);

  if (error !== null) {
    return <div className="px-4 pt-10 text-center text-sm text-primary-dark">{error || t("material.loadFailed")}</div>;
  }
  if (String(type) === "prezentatsiya") {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">{t("material.loading")}</div>;
  }
  if (!item || !config) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">{t("material.loading")}</div>;
  }

  
  
  
  
  
  async function handleRegenerateSlide(index: number) {
    if (!item) return;
    const slides = (content.slides as Record<string, unknown>[] | undefined) ?? [];
    if (index < 0 || index >= slides.length) return;
    setRegeneratingSlide(index);
    try {
      const result = await materialsApi.regeneratePresentationSlide({
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        item_index: index,
        existing_items: slides,
      });
      const nextSlides = slides.map((s, i) => (i === index ? result.item : s));
      const nextContent = { ...content, slides: nextSlides };
      setContent(nextContent);
      await materialsApi.update(type, id, { slides_json: JSON.stringify(nextContent) });
    } catch {
      
    } finally {
      setRegeneratingSlide(null);
    }
  }
  
  
  
  
  
  
  
  
  
  
  async function handleChatEdit(instruction: string) {
    if (!item || !instruction.trim()) return;
    setChatError(null);
    setChatSubmitting(true);
    try {
      const result = await materialsApi.chatEdit({
        material_type: type,
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        instruction,
        content,
      });
      setContent(result.content);
      const field = CONTENT_FIELD[type];
      await materialsApi.update(type, id, { [field]: JSON.stringify(result.content) });
      setChatInstruction("");
    } catch (err) {
      setChatError(err instanceof ApiError ? err.message : t("material.editFailed"));
    } finally {
      setChatSubmitting(false);
    }
  }

  async function handleDocumentSave(patch: Record<string, unknown>) {
    if (!item) return;
    const nextContent = { ...content, ...patch };
    const nextTitle = typeof patch.title === "string" ? patch.title : item.title;
    const updated = await materialsApi.update(type, id, {
      content: JSON.stringify(nextContent),
      title: nextTitle,
    });
    setContent(nextContent);
    setItem((current) => current ? { ...current, title: nextTitle } : updated);
  }

  async function handleToggleFavorite() {
    if (!item) return;
    const next = !item.is_favorite;
    setItem((current) => current ? { ...current, is_favorite: next } : current);
    try {
      await materialsApi.update(type, id, { is_favorite: next });
    } catch {
      setItem((current) => current ? { ...current, is_favorite: !next } : current);
    }
  }

  async function copyDocumentText() {
    const text = document.querySelector<HTMLElement>(".prose-doc, .test-workspace__paper, .practical-workspace__paper")?.innerText?.trim();
    if (text) await navigator.clipboard?.writeText(text);
  }

  async function handleDownload(format: "docx" | "pptx" | "pdf" | "txt") {
    setDownloading(format);
    try {
      
      
      
      
      
      
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(format, { material_type: type, content, language });
    } catch {
      
    } finally {
      setDownloading(null);
    }
  }

  async function handleDelete() {
    if (!item || !confirm(`${t("material.deleteConfirm")} «${item.title}»?`)) return;
    await materialsApi.remove(type, id);
    router.push("/dashboard/materials");
  }

  const Icon = config.icon;
  
  
  
  
  const downloadFormats: Array<"docx" | "pptx" | "pdf" | "txt"> =
    type === "prezentatsiya" ? ["pptx", "pdf"]
    : type === "igra" ? []
    : type === "amaliy" ? ["docx", "pdf"]
    : ["docx", "pdf", "txt"];

  if (type === "konspekt" || type === "lektsiya") {
    return (
      <div className="document-workspace">
        <header className="document-workspace__topbar">
          <button type="button" onClick={() => router.back()} className="document-workspace__icon" aria-label={t("material.back")}>
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="document-workspace__title">
            <span>{item.title}</span>
            <small>{item.subject} · {item.grade}</small>
          </div>
          <div className="document-workspace__actions">
            <button type="button" onClick={handleToggleFavorite} className={`document-workspace__icon ${item.is_favorite ? "is-active" : ""}`} aria-label="Favorite">
              <Bookmark className="h-4 w-4" />
            </button>
            <button type="button" onClick={() => void copyDocumentText()} className="document-workspace__icon" aria-label={t("common.copy")}>
              <Copy className="h-4 w-4" />
            </button>
            <button type="button" onClick={() => window.print()} className="document-workspace__icon" aria-label="Print">
              <span className="text-xs font-semibold">Print</span>
            </button>
            <button type="button" onClick={() => void handleDownload("docx")} disabled={downloading !== null} className="document-workspace__export">
              {downloading === "docx" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              Export
            </button>
            <button type="button" onClick={() => router.back()} className="document-workspace__icon" aria-label={t("common.close")}>
              <X className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="document-workspace__canvas">
          <DocumentEditor
            content={content}
            editable
            onSave={handleDocumentSave}
            isFavorite={item.is_favorite}
            onToggleFavorite={handleToggleFavorite}
            showHeader={false}
          />
        </main>
        <section className="border-t border-border-light bg-white px-4 py-3 shadow-[0_-8px_24px_-20px_rgba(15,23,42,0.35)]">
          <div className="mx-auto max-w-5xl">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-text-secondary">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              {typeof content.language === "string" && content.language === "Таджикский"
                ? "Такмили AI"
                : typeof content.language === "string" && content.language === "Английский"
                  ? "AI refinement"
                  : "Улучшение с AI"}
            </div>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {quickEditOptions(typeof content.language === "string" ? content.language : "Русский").map((action) => (
                <button
                  key={action}
                  type="button"
                  disabled={chatSubmitting}
                  onClick={() => void handleChatEdit(action)}
                  className="rounded-full border border-border-light bg-surface-muted px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:border-primary/30 hover:bg-primary-50 hover:text-primary disabled:pointer-events-none disabled:opacity-50"
                >
                  {action}
                </button>
              ))}
            </div>
            {chatError && <p className="mb-2 text-xs text-primary-dark">{chatError}</p>}
            <form
              className="flex items-center gap-2 rounded-xl border border-border-light px-3 py-2"
              onSubmit={(event) => {
                event.preventDefault();
                void handleChatEdit(chatInstruction);
              }}
            >
              <input
                value={chatInstruction}
                onChange={(event) => setChatInstruction(event.target.value)}
                disabled={chatSubmitting}
                placeholder={t("material.editHint")}
                className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={chatSubmitting || !chatInstruction.trim()}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-40"
                aria-label="Send"
              >
                {chatSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              </button>
            </form>
          </div>
        </section>
      </div>
    );
  }

  if (type === "test") {
    return (
      <TestWorkspace
        item={item}
        content={content}
        onBack={() => router.back()}
        onClose={() => router.back()}
        onToggleFavorite={handleToggleFavorite}
        onCopy={() => void copyDocumentText()}
        onPrint={() => window.print()}
        onEdit={() => router.push(`/dashboard/tests/${id}/edit`)}
        onDownload={() => void handleDownload("pdf")}
        onDelete={() => void handleDelete()}
        downloading={downloading === "pdf"}
      />
    );
  }

  if (type === "amaliy") {
    return (
      <PracticalWorkspace
        item={item}
        content={content}
        onBack={() => router.back()}
        onClose={() => router.back()}
        onToggleFavorite={handleToggleFavorite}
        onCopy={() => void copyDocumentText()}
        onPrint={() => window.print()}
        onDownload={() => void handleDownload("pdf")}
        onDelete={() => void handleDelete()}
        downloading={downloading === "pdf"}
        chatInstruction={chatInstruction}
        setChatInstruction={setChatInstruction}
        chatSubmitting={chatSubmitting}
        chatError={chatError}
        onChatEdit={handleChatEdit}
      />
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 pt-6 sm:px-6">
      <div className="mb-5 flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 rounded-lg border border-border-light bg-white px-2.5 py-1.5 text-sm font-medium text-text-secondary shadow-[0_2px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("material.back")}
        </button>
        <button
          onClick={handleDelete}
          className="flex h-8 w-8 items-center justify-center rounded-lg border border-border-light bg-white text-text-tertiary shadow-[0_2px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:text-primary"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-6 flex items-start gap-3">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${config.bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-text-primary">{item.title}</h1>
          <p className="text-xs text-text-secondary">
            {item.subject} • {item.grade}
          </p>
        </div>
      </div>

      {type === "prezentatsiya" && ((content.slides as Slide[] | undefined)?.length ?? 0) > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          <button
            onClick={() => setPresenting(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary py-2.5 text-sm font-semibold text-white shadow-[0_3px_0_0_var(--color-primary-dark),0_10px_20px_-6px_rgba(220,38,38,0.4)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_4px_0_0_var(--color-primary-dark),0_12px_22px_-6px_rgba(220,38,38,0.45)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark)]"
          >
            <Play className="h-4 w-4" />
            {t("material.openFull")}
          </button>
          {}
          <button
            onClick={() => router.push(`/dashboard/presentations/${id}/edit`)}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-white px-4 py-2.5 text-sm font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5"
          >
            <Pencil className="h-4 w-4" />
            {t("material.edit")}
          </button>
        </div>
      )}

      {}
      {type !== "igra" && type !== "prezentatsiya" && (
        <>
          <PdfPreview
            body={{
              material_type: type,
              content,
              language: typeof content.language === "string" ? content.language : "Русский",
            }}
          />

          <div className="mb-6 flex flex-wrap gap-2">
            {downloadFormats.map((f) => (
              <button
                key={f}
                onClick={() => handleDownload(f)}
                disabled={downloading !== null}
                className="flex items-center gap-1.5 rounded-xl border border-border-light bg-white px-3.5 py-2 text-sm font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/25 hover:text-primary disabled:pointer-events-none disabled:opacity-60"
              >
                {downloading === f ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                .{f}
              </button>
            ))}
          </div>
        </>
      )}

      {type === "prezentatsiya" && (
        <>
          {}
          <div className="mb-6 flex flex-wrap gap-2">
            {downloadFormats.map((f) => (
              <button
                key={f}
                onClick={() => handleDownload(f)}
                disabled={downloading !== null}
                className="flex items-center gap-1.5 rounded-xl border border-border-light bg-white px-3.5 py-2 text-sm font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/25 hover:text-primary disabled:pointer-events-none disabled:opacity-60"
              >
                {downloading === f ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                .{f}
              </button>
            ))}
          </div>
        </>
      )}

      {}
      {type !== "igra" && (
      <div className="mb-6 rounded-2xl border border-border-light bg-white p-3 shadow-[0_3px_0_0_var(--color-border-light),0_14px_28px_-14px_rgba(220,38,38,0.1)]">
        {chatError && <p className="mb-2 px-1 text-xs text-primary-dark">{chatError}</p>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleChatEdit(chatInstruction);
          }}
          className="flex items-center gap-2"
        >
          <Sparkles className="ml-1 h-4 w-4 shrink-0 text-primary" />
          <input
            value={chatInstruction}
            onChange={(e) => setChatInstruction(e.target.value)}
            disabled={chatSubmitting}
            placeholder={t("material.editHint")}
            className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={chatSubmitting || !chatInstruction.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_3px_0_0_var(--color-primary-dark)] active:translate-y-px active:shadow-[0_1px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-40"
          >
            {chatSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </button>
        </form>
      </div>
      )}

      {}
      {(type === "prezentatsiya" || type === "igra") && (
        <>
          {type === "prezentatsiya" && (
            <PresentationBody content={content} onRegenerateSlide={handleRegenerateSlide} regeneratingSlide={regeneratingSlide} />
          )}
          {type === "igra" && <GamePlayer content={content} materialId={id} />}
        </>
      )}

      {presenting && type === "prezentatsiya" && (
        <PresentMode
          slides={(content.slides as Slide[] | undefined) ?? []}
          accent={getSubjectAccent(content.subject as string | undefined)}
          template={KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0]}
          onClose={() => setPresenting(false)}
        />
      )}

    </div>
  );
}

function PracticalWorkspace({
  item,
  content,
  onBack,
  onClose,
  onToggleFavorite,
  onCopy,
  onPrint,
  onDownload,
  onDelete,
  downloading,
  chatInstruction,
  setChatInstruction,
  chatSubmitting,
  chatError,
  onChatEdit,
}: {
  item: MaterialOut;
  content: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onToggleFavorite: () => void;
  onCopy: () => void;
  onPrint: () => void;
  onDownload: () => void;
  onDelete: () => void;
  downloading: boolean;
  chatInstruction: string;
  setChatInstruction: (value: string) => void;
  chatSubmitting: boolean;
  chatError: string | null;
  onChatEdit: (instruction: string) => void;
}) {
  const t = useT();
  const individualTasks = Array.isArray(content.individual_tasks) ? (content.individual_tasks as PracticalTask[]) : [];
  const groupTasks = Array.isArray(content.group_tasks) ? (content.group_tasks as PracticalTask[]) : [];
  const language = typeof content.language === "string" ? content.language.toLowerCase() : "";
  const isTajik = language.includes("тадж") || language.includes("тоҷик") || language.includes("tojik");
  const isEnglish = language.includes("english") || language.includes("англ");
  const labels = isTajik
    ? {
        individual: "Супоришҳои инфиродӣ",
        group: "Супоришҳои гурӯҳӣ",
        instructions: "Дастур",
        outcome: "Натиҷаи интизоршаванда",
        groupSize: "Андозаи гурӯҳ",
        roles: "Нақшҳо",
        tasks: "Супоришҳои амалӣ",
        empty: "Супоришҳои амалӣ ҳоло дастрас нестанд.",
      }
    : isEnglish
      ? {
          individual: "Individual tasks",
          group: "Group tasks",
          instructions: "Instructions",
          outcome: "Expected outcome",
          groupSize: "Group size",
          roles: "Roles",
          tasks: "Practical tasks",
          empty: "No practical tasks are available yet.",
        }
      : {
          individual: "Индивидуальные задания",
          group: "Групповые задания",
          instructions: "Инструкция",
          outcome: "Ожидаемый результат",
          groupSize: "Размер группы",
          roles: "Роли",
          tasks: "Практические задания",
          empty: "Практические задания пока недоступны.",
        };
  const tasks = [
    ...individualTasks.map((task, index) => ({ task, section: labels.individual, group: false, number: index + 1 })),
    ...groupTasks.map((task, index) => ({ task, section: labels.group, group: true, number: individualTasks.length + index + 1 })),
  ];
  const pageSize = 4;
  const pageCount = Math.max(1, Math.ceil(tasks.length / pageSize));
  const [page, setPage] = useState(0);
  const visibleTasks = tasks.slice(page * pageSize, (page + 1) * pageSize);
  const title = typeof content.title === "string" && content.title.trim() ? content.title : item.title;
  const description = typeof content.description === "string" ? content.description : "";

  return (
    <div className="test-workspace practical-workspace">
      <header className="test-workspace__topbar">
        <button type="button" onClick={onBack} className="test-workspace__icon" aria-label="Back"><ArrowLeft className="h-4 w-4" /></button>
        <div className="test-workspace__title">
          <span>{item.title}</span>
          <small>{item.subject} · {item.grade}</small>
        </div>
        <div className="test-workspace__actions">
          <button type="button" onClick={onToggleFavorite} className={`test-workspace__icon ${item.is_favorite ? "is-active" : ""}`} aria-label="Favorite"><Bookmark className="h-4 w-4" /></button>
          <button type="button" onClick={onPrint} className="test-workspace__icon" aria-label="Print"><Printer className="h-4 w-4" /></button>
          <button type="button" onClick={onCopy} className="test-workspace__icon" aria-label="Copy"><Copy className="h-4 w-4" /></button>
          <button type="button" onClick={onDownload} disabled={downloading} className="test-workspace__export" aria-label="Export">
            {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} Export
          </button>
          <button type="button" onClick={onDelete} className="test-workspace__icon" aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
          <button type="button" onClick={onClose} className="test-workspace__icon" aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
      </header>

      <main className="test-workspace__canvas">
        <div className="test-workspace__pager">
          <button type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0} aria-label="Previous page">‹</button>
          <span>{page + 1} of {pageCount}</span>
          <button type="button" onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} disabled={page >= pageCount - 1} aria-label="Next page">›</button>
        </div>
        <article className="test-workspace__paper practical-workspace__paper">
          <header className="test-workspace__paper-header">
            <h1>{title}</h1>
            <p>{item.subject} · {item.grade} · {labels.tasks}</p>
            {description && <p className="practical-workspace__description"><MathText text={description} /></p>}
          </header>
          <div className="practical-workspace__tasks">
            {visibleTasks.map((entry, index) => {
              const task = entry.task;
              const previous = visibleTasks[index - 1];
              return (
                <div key={`${entry.number}-${task.title ?? "task"}`}>
                  {(!previous || previous.section !== entry.section) && <h2 className="practical-workspace__section-title">{entry.section}</h2>}
                  <section className="practical-workspace__task">
                    <div className="practical-workspace__task-head">
                      <h3>{entry.number}. <MathText text={task.title || labels.tasks} /></h3>
                      {task.difficulty && <span>{task.difficulty}</span>}
                    </div>
                    {entry.group && task.group_size && <p><b>{labels.groupSize}:</b> {task.group_size}</p>}
                    {task.instructions && <p><b>{labels.instructions}:</b> <MathText text={task.instructions} /></p>}
                    {entry.group && Array.isArray(task.roles) && task.roles.length > 0 && (
                      <div className="practical-workspace__roles">
                        <b>{labels.roles}:</b>
                        <ul>{task.roles.map((role, roleIndex) => <li key={`${roleIndex}-${role}`}><MathText text={role} /></li>)}</ul>
                      </div>
                    )}
                    {task.expected_outcome && (
                      <div className="practical-workspace__outcome">
                        <b>{labels.outcome}</b>
                        <p><MathText text={task.expected_outcome} /></p>
                      </div>
                    )}
                  </section>
                </div>
              );
            })}
            {tasks.length === 0 && <p className="test-workspace__empty">{labels.empty}</p>}
          </div>
        </article>
      </main>

      <section className="border-t border-border-light bg-white px-4 py-3 shadow-[0_-8px_24px_-20px_rgba(15,23,42,0.35)]">
        <div className="mx-auto max-w-5xl">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-text-secondary">
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            {isTajik ? "Такмили AI" : isEnglish ? "AI refinement" : "Улучшение с AI"}
          </div>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {quickEditOptions(typeof content.language === "string" ? content.language : "Русский").map((action) => (
              <button
                key={action}
                type="button"
                disabled={chatSubmitting}
                onClick={() => onChatEdit(action)}
                className="rounded-full border border-border-light bg-surface-muted px-3 py-1.5 text-xs font-medium text-text-secondary transition hover:border-primary/30 hover:bg-primary-50 hover:text-primary disabled:pointer-events-none disabled:opacity-50"
              >
                {action}
              </button>
            ))}
          </div>
          {chatError && <p className="mb-2 text-xs text-primary-dark">{chatError}</p>}
          <form
            className="flex items-center gap-2 rounded-xl border border-border-light px-3 py-2"
            onSubmit={(event) => {
              event.preventDefault();
              onChatEdit(chatInstruction);
            }}
          >
            <input
              value={chatInstruction}
              onChange={(event) => setChatInstruction(event.target.value)}
              disabled={chatSubmitting}
              placeholder={t("material.editHint")}
              className="min-w-0 flex-1 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-tertiary disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={chatSubmitting || !chatInstruction.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-40"
              aria-label="Send"
            >
              {chatSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function TestWorkspace({
  item,
  content,
  onBack,
  onClose,
  onToggleFavorite,
  onCopy,
  onPrint,
  onEdit,
  onDownload,
  onDelete,
  downloading,
}: {
  item: MaterialOut;
  content: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
  onToggleFavorite: () => void;
  onCopy: () => void;
  onPrint: () => void;
  onEdit: () => void;
  onDownload: () => void;
  onDelete: () => void;
  downloading: boolean;
}) {
  const questions = Array.isArray(content.questions) ? (content.questions as Question[]) : [];
  const pageSize = 5;
  const pageCount = Math.max(1, Math.ceil(questions.length / pageSize));
  const [page, setPage] = useState(0);
  const language = typeof content.language === "string" ? content.language : "";
  const isTajik = language.toLowerCase().includes("тадж") || language.toLowerCase().includes("тоҷик");
  const isEnglish = language.toLowerCase().includes("англ") || language.toLowerCase().includes("english");
  const labels = isTajik
    ? { name: "Ном ва насаб", grade: "Синф", mark: "Баҳо", instruction: "Ҳар саволро бодиққат хонед. Дар саволҳои интихобӣ ҷавоби дурустро қайд кунед.", test: "Тест" }
    : isEnglish
      ? { name: "Name and surname", grade: "Grade", mark: "Score", instruction: "Read each question carefully and mark the correct answer.", test: "Test" }
      : { name: "Имя и фамилия", grade: "Класс", mark: "Оценка", instruction: "Внимательно прочитайте каждый вопрос и отметьте правильный ответ.", test: "Тест" };
  const visibleQuestions = questions.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="test-workspace">
      <header className="test-workspace__topbar">
        <button type="button" onClick={onBack} className="test-workspace__icon" aria-label="Back"><ArrowLeft className="h-4 w-4" /></button>
        <div className="test-workspace__title">
          <span>{item.title}</span>
          <small>{item.subject} · {item.grade}</small>
        </div>
        <div className="test-workspace__actions">
          <button type="button" onClick={onToggleFavorite} className={`test-workspace__icon ${item.is_favorite ? "is-active" : ""}`} aria-label="Favorite"><Bookmark className="h-4 w-4" /></button>
          <button type="button" onClick={onPrint} className="test-workspace__icon" aria-label="Print"><Printer className="h-4 w-4" /></button>
          <button type="button" onClick={onCopy} className="test-workspace__icon" aria-label="Copy"><Copy className="h-4 w-4" /></button>
          <button type="button" onClick={onEdit} className="test-workspace__icon" aria-label="Edit"><Pencil className="h-4 w-4" /></button>
          <button type="button" onClick={onDownload} disabled={downloading} className="test-workspace__export" aria-label="Export">
            {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} Export
          </button>
          <button type="button" onClick={onDelete} className="test-workspace__icon" aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
          <button type="button" onClick={onClose} className="test-workspace__icon" aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
      </header>

      <div className="test-workspace__toolbar" aria-label="Document toolbar">
        <ToolbarIcon icon={<Undo2 className="h-4 w-4" />} label="Undo" />
        <ToolbarIcon icon={<Redo2 className="h-4 w-4" />} label="Redo" />
        <span className="test-workspace__divider" />
        <span className="test-workspace__select">Paragraph⌄</span>
        <span className="test-workspace__select">Arial⌄</span>
        <span className="test-workspace__font-size">11</span>
        <span className="test-workspace__divider" />
        <ToolbarIcon icon={<Bold className="h-4 w-4" />} label="Bold" />
        <ToolbarIcon icon={<Italic className="h-4 w-4" />} label="Italic" />
        <ToolbarIcon icon={<Underline className="h-4 w-4" />} label="Underline" />
        <ToolbarIcon icon={<Strikethrough className="h-4 w-4" />} label="Strikethrough" />
        <ToolbarIcon icon={<MoreHorizontal className="h-4 w-4" />} label="More" />
        <span className="test-workspace__divider" />
        <ToolbarIcon icon={<Sigma className="h-4 w-4" />} label="Formula" />
        <ToolbarIcon icon={<AlignLeft className="h-4 w-4" />} label="Align" />
        <ToolbarIcon icon={<Table2 className="h-4 w-4" />} label="Table" />
      </div>

      <main className="test-workspace__canvas">
        <div className="test-workspace__pager">
          <button type="button" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0} aria-label="Previous page">‹</button>
          <span>{page + 1} of {pageCount}</span>
          <button type="button" onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))} disabled={page >= pageCount - 1} aria-label="Next page">›</button>
        </div>
        <article className="test-workspace__paper">
          <header className="test-workspace__paper-header">
            <h1>{item.title}</h1>
            <p>{item.subject} · {item.grade}</p>
          </header>
          <div className="test-workspace__student-line">
            <span>{labels.name}</span><i />
            <span>{labels.grade}</span><i />
            <span>{labels.mark}</span><i />
          </div>
          <p className="test-workspace__instruction">{labels.instruction}</p>
          <div className="test-workspace__questions">
            {visibleQuestions.map((question, index) => (
              <section key={`${page * pageSize + index}-${question.question}`} className="test-workspace__question">
                <h2>{page * pageSize + index + 1}. <MathText text={question.question} /></h2>
                {question.options && question.options.length > 0 && (
                  <div className="test-workspace__options">
                    {question.options.map((option, optionIndex) => (
                      <p key={`${optionIndex}-${option}`}><b>{String.fromCharCode(65 + optionIndex)})</b> <MathText text={option} /></p>
                    ))}
                  </div>
                )}
              </section>
            ))}
          </div>
          {questions.length === 0 && <p className="test-workspace__empty">{labels.test}</p>}
        </article>
      </main>
    </div>
  );
}

function ToolbarIcon({ icon, label }: { icon: ReactNode; label: string }) {
  return <button type="button" className="test-workspace__toolbar-button" aria-label={label}>{icon}</button>;
}

function PresentationBody({
  content,
  onRegenerateSlide,
  regeneratingSlide,
}: {
  content: Record<string, unknown>;
  onRegenerateSlide: (index: number) => void;
  regeneratingSlide: number | null;
}) {
  const t = useT();
  const slides = (content.slides as Slide[] | undefined) ?? [];
  const accent = getSubjectAccent(content.subject as string | undefined);
  const tmpl = KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0];
  const serifFont = tmpl.mockup.header === "serif" ? { fontFamily: "Georgia, 'Times New Roman', serif" } : undefined;

  return (
    <div className="space-y-8">
      {slides.map((s, i) => {
        const isRegenerating = regeneratingSlide === i;
        return (
          <div
            key={i}
            
            
            
            
            
            
            className="relative mx-auto flex aspect-[4/3] w-full max-w-5xl flex-col overflow-hidden rounded-xl border bg-white shadow-[0_20px_60px_-32px_rgba(15,23,42,0.4)] sm:aspect-video"
            style={{
              ...serifFont,
              borderColor: `${accent}38`,
            }}
          >
            <button
              onClick={() => onRegenerateSlide(i)}
              disabled={regeneratingSlide !== null}
              title={t("material.regenSlide")}
              className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-surface/90 text-text-secondary shadow-sm hover:bg-surface hover:text-text-primary disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
            </button>
            <div className="relative flex min-h-0 flex-1 flex-col">
              {}
              <div className="pr-12">
                <SlideHeader index={i} title={s.title} accent={accent} header={tmpl.mockup.header} />
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-5 pt-4 sm:p-8 sm:pt-5">
                {(s.bullet_points?.length ?? 0) > 0 && (
                  <ul className="mb-2 space-y-1.5 text-sm text-text-primary">
                    {(s.bullet_points ?? []).map((b, j) => (
                      <li key={j} className="flex gap-2.5">
                        <span
                          className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full"
                          style={{ backgroundColor: accent }}
                          aria-hidden
                        />
                        <span className="min-w-0 break-words leading-relaxed">{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {s.visual && <VisualBlockView visual={s.visual} accent={accent} />}
                {s.speaker_notes && (
                  <p
                    className="mt-2 break-words rounded-lg border-l-[3px] bg-white/70 p-2.5 text-xs italic text-text-secondary backdrop-blur-sm"
                    style={{ borderLeftColor: accent }}
                  >
                    {s.speaker_notes}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

