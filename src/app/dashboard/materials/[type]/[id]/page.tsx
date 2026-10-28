"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Download, FileText, Trash2, Loader2, Undo2, RefreshCw, Pencil, Play, Send, Sparkles, RotateCw } from "lucide-react";
import { materialsApi, downloadMaterial, MaterialOut, MaterialType, ApiError } from "@/lib/api";
import PdfPreview from "@/components/PdfPreview";
import { useT } from "@/lib/i18n";
import { MATERIAL_TYPE_CONFIG, KONSPEKT_TEMPLATES, getSubjectAccent } from "@/lib/material-types";
import KonspektBody from "@/components/konspekt/KonspektBody";
import GamePlayer from "@/components/GamePlayer";
import PresentMode from "@/components/PresentMode";
import VisualBlockView, { VisualBlock, SlideHeader } from "@/components/presentation/SlideVisuals";

interface Question {
  question: string;
  type?: string;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
}

interface Slide {
  title: string;
  bullet_points?: string[];
  speaker_notes?: string;
  visual?: VisualBlock;
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
  
  
  
  
  
  
  
  const [view, setView] = useState<"content" | "pdf">("content");
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
  }, [type, id]);

  if (error) {
    return <div className="px-4 pt-10 text-center text-sm text-primary-dark">{error}</div>;
  }
  if (!item || !config) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">Загрузка...</div>;
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
    try {
      
      
      
      
      
      
      const language = typeof content.language === "string" ? content.language : "Русский";
      await downloadMaterial(format, { material_type: type, content, language });
    } catch {
      
    } finally {
      setDownloading(null);
    }
  }

  async function handleDelete() {
    if (!item || !confirm(`Удалить «${item.title}»?`)) return;
    await materialsApi.remove(type, id);
    router.push("/dashboard/materials");
  }

  const Icon = config.icon;
  
  
  
  
  const downloadFormats: Array<"docx" | "pptx" | "pdf" | "txt"> =
    type === "prezentatsiya" ? ["pptx", "pdf"]
    : type === "igra" ? []
    : type === "amaliy" ? ["docx", "pdf"]
    : ["docx", "pdf", "txt"];

  return (
    <div className="mx-auto max-w-2xl px-4 pt-6 sm:px-6">
      <div className="mb-5 flex items-center justify-between">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm font-medium text-text-secondary"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад
        </button>
        <button onClick={handleDelete} className="text-text-tertiary hover:text-primary">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-6 flex items-start gap-3">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${config.bg}`}>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-text-primary">{item.title}</h1>
          <p className="text-xs text-text-secondary">
            {item.subject} • {item.grade}
          </p>
        </div>
      </div>

      {(type === "konspekt" || type === "lektsiya") && hasUndo && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-primary/20 bg-primary-50 px-4 py-2.5">
          <p className="text-xs text-primary-dark">Раздел изменён. Можно вернуть предыдущую версию.</p>
          <button
            onClick={handleUndo}
            disabled={undoing}
            className="flex shrink-0 items-center gap-1.5 rounded-lg bg-surface px-3 py-1.5 text-xs font-medium text-primary-dark shadow-sm hover:bg-primary-50 disabled:opacity-60"
          >
            {undoing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
            Отменить
          </button>
        </div>
      )}

      {type === "prezentatsiya" && ((content.slides as Slide[] | undefined)?.length ?? 0) > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          <button
            onClick={() => setPresenting(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:bg-primary-dark"
          >
            <Play className="h-4 w-4" />
            Показать на весь экран
          </button>
          {}
          <button
            onClick={() => router.push(`/dashboard/presentations/${id}/edit`)}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-text-primary shadow-sm transition hover:bg-surface-muted"
          >
            <Pencil className="h-4 w-4" />
            Редактировать
          </button>
        </div>
      )}

      {}
      {type === "test" && (content.questions as Question[] | undefined)?.length ? (
        <div className="mb-3 flex">
          <button
            onClick={() => router.push(`/dashboard/tests/${id}/edit`)}
            className="flex items-center justify-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-sm font-semibold text-text-primary shadow-sm transition hover:bg-surface-muted"
          >
            <Pencil className="h-4 w-4" />
            Редактировать тест
          </button>
        </div>
      ) : null}

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
                className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted disabled:opacity-60"
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
                className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3.5 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted disabled:opacity-60"
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
      <div className="mb-6 rounded-2xl border border-border-light bg-surface p-3">
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
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-white disabled:opacity-40"
          >
            {chatSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          </button>
        </form>
      </div>
      )}

      {}
      {((view === "content" && type === "prezentatsiya") || type === "igra") && (
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

function TestBody({
  content,
  onRegenerateQuestion,
  regeneratingQuestion,
}: {
  content: Record<string, unknown>;
  onRegenerateQuestion?: (index: number) => void;
  regeneratingQuestion?: number | null;
}) {
  const description = content.description as string | undefined;
  const questions = (content.questions as Question[] | undefined) ?? [];
  return (
    <div>
      {description && <p className="mb-6 text-sm italic text-text-secondary">{description}</p>}
      {questions.map((q, i) => (
        <div key={i} className="mb-4 rounded-2xl border border-border-light bg-surface p-4">
          <div className="mb-3 flex items-start justify-between gap-2">
            <p className="font-medium text-text-primary">
              {i + 1}. {q.question}
            </p>
            {onRegenerateQuestion && (
              <button
                onClick={() => onRegenerateQuestion(i)}
                disabled={regeneratingQuestion === i}
                title="Пересоздать этот вопрос заново"
                className="shrink-0 rounded-lg p-1 text-text-tertiary hover:bg-surface-muted hover:text-primary disabled:opacity-50"
              >
                <RotateCw className={`h-3.5 w-3.5 ${regeneratingQuestion === i ? "animate-spin" : ""}`} />
              </button>
            )}
          </div>
          {q.type === "open_ended" ? (
            q.model_answer && (
              <p className="rounded-lg bg-surface-muted p-3 text-sm text-text-secondary">
                <span className="font-medium text-primary">Ответ: </span>
                {q.model_answer}
              </p>
            )
          ) : (
            <ul className="space-y-1.5">
              {(q.options ?? []).map((opt, j) => {
                const isCorrect = q.correct_indices ? q.correct_indices.includes(j) : q.correct_index === j;
                return (
                  <li
                    key={j}
                    className={`rounded-lg px-3 py-1.5 text-sm ${
                      isCorrect ? "bg-primary-50 font-medium text-primary-dark" : "text-text-secondary"
                    }`}
                  >
                    {String.fromCharCode(65 + j)}) {opt}
                  </li>
                );
              })}
            </ul>
          )}
          {q.explanation && <p className="mt-2 text-xs italic text-text-tertiary">{q.explanation}</p>}
        </div>
      ))}
    </div>
  );
}

interface PracticalTaskItem {
  title?: string;
  difficulty?: string;
  group_size?: string;
  roles?: string[];
  instructions?: string;
  expected_outcome?: string;
}

const DIFFICULTY_STYLE: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};




function PracticalBody({
  content,
  onRegenerateTask,
  regeneratingTask,
}: {
  content: Record<string, unknown>;
  onRegenerateTask?: (kind: "individual_tasks" | "group_tasks", index: number) => void;
  regeneratingTask?: { kind: "individual_tasks" | "group_tasks"; index: number } | null;
}) {
  const description = content.description as string | undefined;
  const individual = (content.individual_tasks as PracticalTaskItem[] | undefined) ?? [];
  const group = (content.group_tasks as PracticalTaskItem[] | undefined) ?? [];

  function TaskCard({
    task,
    index,
    kind,
  }: {
    task: PracticalTaskItem;
    index: number;
    kind: "individual_tasks" | "group_tasks";
  }) {
    const isRegenerating = regeneratingTask?.kind === kind && regeneratingTask.index === index;
    return (
      <div className="mb-4 rounded-2xl border border-border-light bg-surface p-4">
        <div className="mb-2 flex items-start justify-between gap-2">
          <p className="font-medium text-text-primary">
            {index + 1}. {task.title}
          </p>
          <div className="flex shrink-0 items-center gap-1.5">
            {task.difficulty && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${
                  DIFFICULTY_STYLE[task.difficulty.toLowerCase()] ?? "bg-surface-muted text-text-secondary"
                }`}
              >
                {task.difficulty}
              </span>
            )}
            {onRegenerateTask && (
              <button
                onClick={() => onRegenerateTask(kind, index)}
                disabled={isRegenerating}
                title="Пересоздать это задание заново"
                className="rounded-lg p-1 text-text-tertiary hover:bg-surface-muted hover:text-primary disabled:opacity-50"
              >
                <RotateCw className={`h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
              </button>
            )}
          </div>
        </div>
        {task.group_size && <p className="mb-2 text-xs text-text-tertiary">{task.group_size}</p>}
        {task.instructions && <p className="mb-2 text-sm text-text-secondary">{task.instructions}</p>}
        {(task.roles?.length ?? 0) > 0 && (
          <ul className="mb-2 space-y-1 text-sm text-text-secondary">
            {task.roles!.map((role, j) => (
              <li key={j}>• {role}</li>
            ))}
          </ul>
        )}
        {task.expected_outcome && (
          <p className="rounded-lg bg-surface-muted p-2.5 text-xs text-text-tertiary">{task.expected_outcome}</p>
        )}
      </div>
    );
  }

  return (
    <div>
      {description && <p className="mb-6 text-sm italic text-text-secondary">{description}</p>}
      {individual.length > 0 && (
        <>
          <h3 className="mb-3 text-sm font-bold text-text-primary">Индивидуальные задания</h3>
          {individual.map((t, i) => (
            <TaskCard key={i} task={t} index={i} kind="individual_tasks" />
          ))}
        </>
      )}
      {group.length > 0 && (
        <>
          <h3 className="mb-3 mt-4 text-sm font-bold text-text-primary">Групповые задания</h3>
          {group.map((t, i) => (
            <TaskCard key={i} task={t} index={i} kind="group_tasks" />
          ))}
        </>
      )}
    </div>
  );
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
    <div>
      {slides.map((s, i) => {
        const isRegenerating = regeneratingSlide === i;
        return (
          <div
            key={i}
            
            
            
            
            
            
            className="relative mb-4 overflow-hidden rounded-2xl border shadow-sm"
            style={{
              ...serifFont,
              borderColor: `${accent}22`,
              background: `linear-gradient(135deg, ${accent}0d 0%, #ffffff 45%, ${accent}12 100%)`,
            }}
          >
            <div
              className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl"
              style={{ backgroundColor: `${accent}1f` }}
              aria-hidden
            />
            <div
              className="pointer-events-none absolute -bottom-20 -left-12 h-44 w-44 rounded-full blur-3xl"
              style={{ backgroundColor: `${accent}14` }}
              aria-hidden
            />
            <span
              className="pointer-events-none absolute -bottom-4 right-3 select-none text-[clamp(4rem,18vw,7rem)] font-black leading-none sm:-bottom-6 sm:right-4"
              style={{ color: `${accent}0f` }}
              aria-hidden
            >
              {i + 1}
            </span>

            <button
              onClick={() => onRegenerateSlide(i)}
              disabled={regeneratingSlide !== null}
              title={t("material.regenSlide")}
              className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-surface/90 text-text-secondary shadow-sm hover:bg-surface hover:text-text-primary disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
            </button>
            <div className="relative">
              {}
              <div className="pr-12">
                <SlideHeader index={i} title={s.title} accent={accent} header={tmpl.mockup.header} />
              </div>
              <div className="p-4 pt-3">
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

