"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ChevronDown, Download, Trash2, Loader2, Undo2, Pencil, Play, Send, Sparkles } from "lucide-react";
import { materialsApi, downloadMaterial, MaterialOut, MaterialType, ApiError, type BookSourceReference } from "@/lib/api";
import PdfPreview from "@/components/PdfPreview";
import { useT } from "@/lib/i18n";
import { MATERIAL_TYPE_CONFIG, KONSPEKT_TEMPLATES, getSubjectAccent } from "@/lib/material-types";
import KonspektBody from "@/components/konspekt/KonspektBody";
import KonspektToc from "@/components/konspekt/KonspektToc";
import GamePlayer from "@/components/GamePlayer";
import PresentMode from "@/components/PresentMode";
import PresentationViewer, { type Slide } from "@/components/presentation/PresentationViewer";
import TestViewer from "@/components/test/TestViewer";
import PracticalViewer from "@/components/practical/PracticalViewer";

interface Question {
  question: string;
  type?: string;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
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
  const [actionError, setActionError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [fetchingImage, setFetchingImage] = useState(false);
  const [replacingLessonImage, setReplacingLessonImage] = useState<number | null>(null);
  const [uploadingLessonImage, setUploadingLessonImage] = useState<number | null>(null);
  const [regeneratingSlide, setRegeneratingSlide] = useState<number | null>(null);
  const [regeneratingQuestion, setRegeneratingQuestion] = useState<number | null>(null);
  const [regeneratingTask, setRegeneratingTask] = useState<{ kind: "individual_tasks" | "group_tasks"; index: number } | null>(null);
  const [hasUndo, setHasUndo] = useState(false);
  const [undoing, setUndoing] = useState(false);
  const [presenting, setPresenting] = useState(false);
  
  
  
  
  
  
  
  const [chatInstruction, setChatInstruction] = useState("");
  const [chatSubmitting, setChatSubmitting] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  useEffect(() => {
    materialsApi
      .get(type, id)
      .then((loaded) => {
        setItem(loaded);
        setHasUndo(Boolean(loaded.has_undo));
        const raw = loaded.content ?? loaded.questions_json ?? loaded.slides_json ?? loaded.tasks_json ?? loaded.game_json ?? "{}";
        try {
          setContent(JSON.parse(raw));
        } catch {
          setContent({});
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : t("material.loadFailed")));
  }, [type, id, t]);

  if (error) {
    return <div className="px-4 pt-10 text-center text-sm text-error">{error}</div>;
  }
  if (!item || !config) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">{t("common.loading")}</div>;
  }

  
  
  
  
  
  async function handleRegenerateSection(section: string) {
    if (!item) return;
    setRegenerating(section);
    try {
      const result = await materialsApi.regenerateKonspektSection(
        {
          topic: item.title,
          subject: item.subject,
          language: typeof content.language === "string" ? content.language : "Русский",
          level: typeof content.level === "string" ? content.level : "Средний",
          grade: item.grade,
          section,
          existing_content: content,
        },
        type === "lektsiya" ? "lektsiya" : "konspekt"
      );
      const nextContent = { ...content, ...result.item };
      setContent(nextContent);
      const updated = await materialsApi.update(type, id, { content: JSON.stringify(nextContent) });
      
      
      
      setHasUndo(Boolean(updated.has_undo));
    } catch {
      
    } finally {
      setRegenerating(null);
    }
  }

  
  
  
  
  async function handleFetchImage() {
    if (!item || (type !== "konspekt" && type !== "lektsiya")) return;
    setFetchingImage(true);
    try {
      const updated = await materialsApi.fetchMissingImage(id, type);
      const raw = updated.content ?? "{}";
      setContent(JSON.parse(raw));
    } catch {
      
    } finally {
      setFetchingImage(false);
    }
  }

  
  
  
  async function handleReplaceLessonImage(index: number) {
    if (!item || (type !== "konspekt" && type !== "lektsiya")) return;
    setReplacingLessonImage(index);
    try {
      const updated = await materialsApi.replaceLessonImage(id, index, type);
      const raw = updated.content ?? "{}";
      setContent(JSON.parse(raw));
    } catch {
      
    } finally {
      setReplacingLessonImage(null);
    }
  }

  
  
  async function handleUploadLessonImage(index: number, file: File) {
    if (!item || (type !== "konspekt" && type !== "lektsiya")) return;
    setUploadingLessonImage(index);
    try {
      const updated = await materialsApi.uploadLessonImage(id, index, file, type);
      const raw = updated.content ?? "{}";
      setContent(JSON.parse(raw));
    } catch {
      
    } finally {
      setUploadingLessonImage(null);
    }
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

  
  
  
  async function handleRegenerateQuestion(index: number) {
    if (!item) return;
    const questions = (content.questions as Record<string, unknown>[] | undefined) ?? [];
    if (index < 0 || index >= questions.length) return;
    setRegeneratingQuestion(index);
    try {
      const result = await materialsApi.regenerateTestQuestion({
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        item_index: index,
        existing_items: questions,
      });
      const nextQuestions = questions.map((q, i) => (i === index ? result.item : q));
      const nextContent = { ...content, questions: nextQuestions };
      setContent(nextContent);
      await materialsApi.update(type, id, { questions_json: JSON.stringify(nextContent) });
    } catch {
      
    } finally {
      setRegeneratingQuestion(null);
    }
  }

  
  
  
  async function handleRegeneratePracticalTask(kind: "individual_tasks" | "group_tasks", index: number) {
    if (!item) return;
    const items = (content[kind] as Record<string, unknown>[] | undefined) ?? [];
    if (index < 0 || index >= items.length) return;
    setRegeneratingTask({ kind, index });
    try {
      const result = await materialsApi.regeneratePracticalTask({
        topic: item.title,
        subject: item.subject,
        language: typeof content.language === "string" ? content.language : "Русский",
        level: typeof content.level === "string" ? content.level : "Средний",
        grade: item.grade,
        item_index: index,
        existing_items: items,
        kind,
      });
      const nextItems = items.map((t, i) => (i === index ? result.item : t));
      const nextContent = { ...content, [kind]: nextItems };
      setContent(nextContent);
      await materialsApi.update(type, id, { tasks_json: JSON.stringify(nextContent) });
    } catch {
      
    } finally {
      setRegeneratingTask(null);
    }
  }

  
  
  async function handleUndo() {
    setUndoing(true);
    try {
      const restored = await materialsApi.undoKonspektContent(id, type === "lektsiya" ? "lektsiya" : "konspekt");
      setHasUndo(Boolean(restored.has_undo));
      const raw = restored.content ?? "{}";
      try {
        setContent(JSON.parse(raw));
      } catch {
        
      }
    } catch {
      
    } finally {
      setUndoing(false);
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
      const updated = await materialsApi.update(type, id, { [field]: JSON.stringify(result.content) });
      if (type === "konspekt" || type === "lektsiya") setHasUndo(Boolean(updated.has_undo));
      setChatInstruction("");
    } catch (err) {
      setChatError(err instanceof ApiError ? err.message : t("material.editFailed"));
    } finally {
      setChatSubmitting(false);
    }
  }

  async function handleDownload(format: "docx" | "pptx" | "pdf" | "txt") {
    setDownloading(format);
    setActionError(null);
    try {
      
      
      
      
      
      
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(format, { material_type: type, content, language });
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : t("material.downloadFailed"));
    } finally {
      setDownloading(null);
    }
  }

  async function handleDelete() {
    if (!item || !confirm(`${t("material.confirmDelete")} «${item.title}»?`)) return;
    try {
      await materialsApi.remove(type, id);
      router.push("/dashboard/materials");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : t("common.error"));
    }
  }

  const Icon = config.icon;
  
  
  
  
  const downloadFormats: Array<"docx" | "pptx" | "pdf" | "txt"> =
    type === "prezentatsiya" ? ["pptx", "pdf"]
    : type === "igra" ? []
    : type === "amaliy" ? ["docx", "pdf"]
    : ["docx", "pdf", "txt"];

  const wide = type === "prezentatsiya" || type === "konspekt" || type === "lektsiya";
  const slides = (content.slides as Slide[] | undefined) ?? [];
  const questions = (content.questions as Question[] | undefined) ?? [];
  /* item.subject, not content.subject: the subject is a real, always-present
   * column on the material itself, but the generated content JSON does not
   * reliably carry its own copy of it (seeded/older/regenerated content may
   * not). Reading from content fell through to getSubjectAccent's default —
   * which is blue — on exactly the material types this redesign explicitly
   * rules blue out for. */
  const accent = getSubjectAccent(item.subject);
  const language = typeof content.language === "string" ? content.language : "Русский";
  const source = content.source && typeof content.source === "object"
    ? content.source as BookSourceReference : null;
  /* The generic embedded-PDF preview used to be the entire viewing
   * experience for every type that is not a konspekt, a lecture or a
   * presentation — tests and practical tasks had no reading layout of
   * their own at all, just this iframe. It is still real and still the
   * exact file a download produces, so it stays, but now as the second
   * thing on the page confirming the first, not the only thing. */
  const showFileExport = type !== "igra" && type !== "prezentatsiya";

  return (
    <div className={`mx-auto px-4 pt-6 sm:px-6 ${wide ? "max-w-5xl lg:px-8" : "max-w-2xl"}`}>
      <div className="mb-5 flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-meta font-medium text-text-secondary transition-colors duration-150 hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("common.back")}
        </button>
        <button onClick={handleDelete} aria-label={t("material.delete")} title={t("material.delete")} className="rounded-control p-2 text-text-tertiary transition-colors duration-150 hover:bg-error/10 hover:text-error">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-6 flex items-start gap-3">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-control ${config.bg}`}>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </div>
        <div className="min-w-0">
          <h1 className="text-heading font-semibold text-text-primary">{item.title}</h1>
          <p className="text-meta text-text-secondary">
            {item.subject} · {item.grade}
          </p>
        </div>
      </div>

      {source && <div className="mb-6 rounded-xl border border-primary/15 bg-primary-50/50 px-4 py-3 text-sm text-text-secondary">
        <p className="font-semibold text-text-primary">{t("book.source")}: {source.document_title}</p>
        <p className="mt-1">{t("book.usedPages")}: {source.used_pages.join(", ")}</p>
        {source.unreadable_pages?.length > 0 && <p className="mt-1">{t("book.unreadable")}: {source.unreadable_pages.join(", ")}</p>}
        {source.selection_is_excerpt && <p className="mt-2">{t("book.excerptNote")}</p>}
        <p className="mt-2 text-xs">{t("book.groundingNote")}</p>
      </div>}

      {(type === "konspekt" || type === "lektsiya") && hasUndo && (
        <div className="mb-5 flex items-center justify-between gap-3 rounded-control border border-primary/20 bg-primary-50 px-4 py-2.5">
          <p className="text-meta text-primary-accent">{t("material.undoHint")}</p>
          <button
            onClick={handleUndo}
            disabled={undoing}
            className="flex shrink-0 items-center gap-1.5 rounded-control bg-surface px-3 py-1.5 text-meta font-medium text-primary-accent shadow-card transition-colors duration-150 hover:bg-primary-50 disabled:opacity-60"
          >
            {undoing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
            {t("material.undo")}
          </button>
        </div>
      )}

      {/* ---- Toolbar: one row per type, not a separate row per action ---- */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {type === "prezentatsiya" && slides.length > 0 && (
          <>
            <button
              onClick={() => setPresenting(true)}
              className="flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-meta font-semibold text-white shadow-card transition-colors duration-150 hover:bg-primary-dark"
            >
              <Play className="h-4 w-4" />
              {t("material.present")}
            </button>
            <button
              onClick={() => router.push(`/dashboard/presentations/${id}/edit`)}
              className="flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-meta font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted"
            >
              <Pencil className="h-4 w-4" />
              {t("material.edit")}
            </button>
          </>
        )}

        {type === "test" && questions.length > 0 && (
          <button
            onClick={() => router.push(`/dashboard/tests/${id}/edit`)}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-meta font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted"
          >
            <Pencil className="h-4 w-4" />
            {t("material.editTest")}
          </button>
        )}

        {type !== "igra" && (
          <details className="group relative">
            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-meta font-semibold text-text-primary hover:bg-surface-muted">
              {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {t("material.download")}
              <ChevronDown className="h-4 w-4 text-text-tertiary group-open:rotate-180" />
            </summary>
            <div className="absolute left-0 top-full z-20 mt-1 min-w-36 rounded-control border border-border bg-surface p-1 shadow-float">
              {downloadFormats.map((format) => (
                <button key={format} type="button" onClick={() => handleDownload(format)} disabled={downloading !== null}
                  className="flex w-full items-center gap-2 rounded-control px-3 py-2 text-left text-meta font-medium uppercase text-text-primary hover:bg-surface-muted disabled:opacity-50">
                  {downloading === format ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                  {format}
                </button>
              ))}
            </div>
          </details>
        )}
      </div>
      {actionError && <p role="alert" className="mb-5 rounded-control border border-error/30 bg-error/10 px-4 py-3 text-meta text-error">{actionError}</p>}

      {/* ---- The actual reading experience, one per type ---- */}
      {(type === "konspekt" || type === "lektsiya") && (
        <div className="grid gap-8 lg:grid-cols-[12rem_minmax(0,1fr)]">
          <div className="hidden lg:block">
            <div className="sticky top-6">
              <KonspektToc content={content} language={language} />
            </div>
          </div>
          <div className="min-w-0 max-w-[42rem]">
            <KonspektBody
              content={content}
              language={language}
              onRegenerate={handleRegenerateSection}
              regenerating={regenerating}
              onFetchImage={handleFetchImage}
              fetchingImage={fetchingImage}
              onReplaceLessonImage={handleReplaceLessonImage}
              replacingLessonImage={replacingLessonImage}
              onUploadLessonImage={handleUploadLessonImage}
              uploadingLessonImage={uploadingLessonImage}
            />
          </div>
        </div>
      )}

      {type === "prezentatsiya" && slides.length > 0 && (
        <PresentationViewer
          content={content}
          accent={accent}
          language={language}
          onRegenerateSlide={handleRegenerateSlide}
          regeneratingSlide={regeneratingSlide}
        />
      )}

      {type === "test" && <TestViewer content={content} language={language} onRegenerateQuestion={handleRegenerateQuestion} regeneratingQuestion={regeneratingQuestion} />}

      {type === "amaliy" && (
        <PracticalViewer content={content} language={language} onRegenerateTask={handleRegeneratePracticalTask} regeneratingTask={regeneratingTask} />
      )}

      {type === "igra" && <GamePlayer content={content} materialId={id} />}

      {type !== "igra" && (
        <div className="mt-8 rounded-card border border-border-light bg-surface p-4">
          <p className="mb-3 text-meta font-semibold text-text-primary">{t("material.aiEditTitle")}</p>
          {chatError && <p className="mb-2 px-1 text-micro text-primary-accent">{chatError}</p>}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleChatEdit(chatInstruction);
            }}
            className="flex items-center gap-2"
          >
            <Sparkles className="ml-1 h-4 w-4 shrink-0 text-primary-accent" />
            <input
              value={chatInstruction}
              onChange={(e) => setChatInstruction(e.target.value)}
              disabled={chatSubmitting}
              placeholder={t("material.editHint")}
              aria-label={t("material.editHint")}
              className="min-w-0 flex-1 bg-transparent text-meta text-text-primary outline-none placeholder:text-text-tertiary disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={chatSubmitting || !chatInstruction.trim()}
              aria-label={t("material.aiEditTitle")}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-primary text-white transition-colors duration-150 hover:bg-primary-dark disabled:opacity-40"
            >
              {chatSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </form>
        </div>
      )}

      {showFileExport && (
        <div className="mt-8">
          <p className="mb-2.5 text-micro font-semibold uppercase tracking-wide text-text-tertiary">{t("material.pdfPreview")}</p>
          <PdfPreview key={JSON.stringify(content)} body={{ material_type: type, content, language }} />
        </div>
      )}

      {presenting && type === "prezentatsiya" && (
        <PresentMode
          slides={slides}
          accent={accent}
          language={language}
          template={KONSPEKT_TEMPLATES.find((t) => t.id === content.template) ?? KONSPEKT_TEMPLATES[0]}
          onClose={() => setPresenting(false)}
        />
      )}
    </div>
  );
}
