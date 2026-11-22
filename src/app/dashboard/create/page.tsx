"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Download, Check, Sparkles, ArrowRight, BookOpen } from "lucide-react";
import {
  materialsApi, downloadAllZip, ApiError, type GenerateAllResult, type MaterialType,
} from "@/lib/api";
import { bookApi, type BookLibraryItem, type BookSource, type BookTopicsStatus } from "@/lib/book-api";
import { useT } from "@/lib/i18n";
import CreationAssistant from "@/components/dashboard/CreationAssistant";
import LessonDesignPanel, {
  type LessonDesignContext,
} from "@/components/dashboard/LessonDesignPanel";
import { lessonFrameworkFor } from "@/lib/lesson-frameworks";
import { consumeWasBackNavigation } from "@/lib/back-navigation";
import {
  MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY, LANGUAGES, LANGUAGE_LABEL_KEYS, LEVELS, CLASSES, SUBJECTS,
  SUBJECT_LABEL_KEYS, TEST_TYPES, TEST_TYPE_LABEL_KEYS,
} from "@/lib/material-types";

const FIELD =
  "w-full rounded-xl border border-border bg-white px-4 py-3 text-sm text-text-primary shadow-[inset_0_2px_3px_rgba(0,0,0,0.04)] outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10";
const SELECT = `${FIELD} appearance-none`;

/* Literal gradient classes per type, not a runtime-built string — Tailwind
 * only emits utilities it finds as literal text in source. */
const CARD_BG: Record<CreatableType, string> = {
  konspekt: "bg-gradient-to-br from-note-bg/50 to-white",
  lektsiya: "bg-gradient-to-br from-lecture-bg/50 to-white",
  test: "bg-gradient-to-br from-test-bg/50 to-white",
  prezentatsiya: "bg-gradient-to-br from-pres-bg/50 to-white",
  amaliy: "bg-gradient-to-br from-amaliy-bg/50 to-white",
};

type CreatableType = Exclude<MaterialType, "igra">;
const TYPES: CreatableType[] = ["konspekt", "lektsiya", "test", "prezentatsiya", "amaliy"];


const COUNT_PRESETS = [5, 10, 15];

const RESULT_STORAGE_KEY = "dastyor:create:result";

type AssistantStep = 1 | 2 | 3;
type AssistantAnswers = { goal?: string; level?: string; source?: "library" | "uploaded" | "pasted" | "none" };

const DEFAULT_LESSON_DESIGN: LessonDesignContext = {
  frameworkId: "gagne",
  duration: "45 minutes",
  classSize: "",
  deliveryMode: "Face-to-face",
  learnerProfile: "",
  existingObjectives: "",
  previouslyCovered: "",
  comingNext: "",
  priorKnowledge: "",
  assessmentContext: "",
  aiPolicy: "Permitted with acknowledgement",
};


function loadPersistedResult(): { topic: string; result: GenerateAllResult } | null {
  if (typeof window === "undefined") return null;
  try {
    if (!consumeWasBackNavigation()) return null;
    const raw = sessionStorage.getItem(RESULT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}


export default function CreatePage() {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();

  const persisted = useState(loadPersistedResult)[0];
  const generationRef = useRef<AbortController | null>(null);
  const [topic, setTopic] = useState(persisted?.topic ?? "");
  const [grade, setGrade] = useState(CLASSES[6]);
  const [subject, setSubject] = useState(SUBJECTS[0]);
  const [language, setLanguage] = useState(LANGUAGES[0]);
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  const [selected, setSelected] = useState<CreatableType[]>(() => {
    const wanted = params.get("type");
    if (wanted === "all") return [...TYPES];
    if (wanted && (TYPES as string[]).includes(wanted)) return [wanted as CreatableType];
    return [];
  });
  const [slideCount, setSlideCount] = useState(10);
  const [questionCount, setQuestionCount] = useState(10);
  
  
  const [testType, setTestType] = useState("mixed");
  const [includeExamples, setIncludeExamples] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateAllResult | null>(persisted?.result ?? null);
  const [zipping, setZipping] = useState(false);
  const [clarifyQuestion, setClarifyQuestion] = useState<string | null>(null);
  const [clarifyOptions, setClarifyOptions] = useState<string[]>([]);
  const [showCustomClarification, setShowCustomClarification] = useState(false);
  const [customClarification, setCustomClarification] = useState("");
  const [assistantStep, setAssistantStep] = useState<AssistantStep | null>(null);
  const [assistantAnswers, setAssistantAnswers] = useState<AssistantAnswers>({});
  const [sourceText, setSourceText] = useState<string | null>(null);
  const [sourceFileName, setSourceFileName] = useState<string | null>(null);
  const [pastedSourceText, setPastedSourceText] = useState("");
  const [sourceTruncated, setSourceTruncated] = useState(false);
  const [sourceUploading, setSourceUploading] = useState(false);
  const [selectedLibraryBook, setSelectedLibraryBook] = useState<BookLibraryItem | null>(null);
  const [librarySource, setLibrarySource] = useState<BookSource | null>(null);
  const [librarySelecting, setLibrarySelecting] = useState(false);
  const [libraryBooks, setLibraryBooks] = useState<BookLibraryItem[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);
  const [libraryAutoFound, setLibraryAutoFound] = useState(false);
  const [libraryAutoMissing, setLibraryAutoMissing] = useState(false);
  const [bookTopicsStatus, setBookTopicsStatus] = useState<BookTopicsStatus | null>(null);
  const [topicFocused, setTopicFocused] = useState(false);
  const [lessonDesign, setLessonDesign] = useState<LessonDesignContext>(DEFAULT_LESSON_DESIGN);

  const allChosen = selected.length === TYPES.length;

  const libraryCopy = language === "Таджикский"
    ? {
        title: "Китоб интихоб карда шуд",
        foundHint: "AI маводро аз рӯйи ин китоб месозад.",
        pickTitle: "Китобро интихоб кунед",
        hint: "Интихоби китоб ҳатмист. AI маводро танҳо аз рӯйи китоби интихобшуда месозад.",
        empty: "Барои ин синф ва фан дар китобхона китобе ёфт нашуд. Лутфан худатон китоберо боргирӣ кунед ё дастӣ интихоб кунед.",
        required: "Аввал як китобро интихоб кунед.",
        loading: "Китоби мувофиқро ҷустуҷӯ карда истодаем…",
      }
    : language === "Английский"
      ? {
          title: "Textbook found",
          foundHint: "AI will create the material from this book.",
          pickTitle: "Choose a textbook",
          hint: "Choosing a book is required. AI will create the material from the selected textbook.",
          empty: "No matching book was found in the library for this grade and subject. Upload one yourself or pick it manually below.",
          required: "Choose a book first.",
          loading: "Looking for a matching textbook…",
        }
      : {
          title: "Учебник найден",
          foundHint: "AI создаст материал по этому учебнику.",
          pickTitle: "Выберите учебник",
          hint: "Выбор книги обязателен. AI создаст материал только по выбранному учебнику.",
          empty: "Для этого класса и предмета в библиотеке не нашлось подходящего учебника. Загрузите его сами или выберите вручную ниже.",
          required: "Сначала выберите учебник.",
          loading: "Ищем подходящий учебник…",
        };

  useEffect(() => {
    const controller = new AbortController();
    void bookApi.autoSelect(subject, grade, controller.signal)
      .then(({ book, source, topics }) => {
        setSelectedLibraryBook(book);
        setLibrarySource(source);
        setSourceFileName(book.title);
        setLibraryAutoFound(true);
        setBookTopicsStatus(topics);
      })
      .catch(() => {
        if (controller.signal.aborted) return;
        setLibraryAutoMissing(true);
        // Fall back to the manual catalog (filtered the same way) so the
        // teacher can still pick a book by hand instead of being blocked.
        void bookApi.library(subject, grade, controller.signal)
          .then(setLibraryBooks)
          .catch(() => setLibraryBooks([]));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLibraryLoading(false);
      });
    return () => controller.abort();
  }, [subject, grade]);

  function toggle(type: CreatableType) {
    setSelected((prev) =>
      prev.includes(type) ? prev.filter((x) => x !== type) : [...prev, type],
    );
  }

  function resetLibrarySelection() {
    setLibraryLoading(true);
    setLibraryAutoFound(false);
    setLibraryAutoMissing(false);
    setLibraryBooks([]);
    setSelectedLibraryBook(null);
    setLibrarySource(null);
    setBookTopicsStatus(null);
  }

  // Topics are usually ready immediately (cached, or computed synchronously
  // the first time a book is opened), but poll briefly in case a future
  // re-processing pass leaves a book "pending" right when it's selected.
  useEffect(() => {
    if (bookTopicsStatus?.status !== "pending" || !selectedLibraryBook) return;
    const bookId = selectedLibraryBook.id;
    let cancelled = false;
    let attempts = 0;
    const poll = () => {
      if (cancelled) return;
      void bookApi.topics(bookId).then((next) => {
        if (cancelled) return;
        setBookTopicsStatus(next);
        attempts += 1;
        if (next.status === "pending" && attempts < 10) {
          timer = setTimeout(poll, 2000);
        }
      }).catch(() => {});
    };
    let timer = setTimeout(poll, 2000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [bookTopicsStatus?.status, selectedLibraryBook]);

  const topicSuggestions = useMemo(() => {
    const all = bookTopicsStatus?.status === "ready" ? bookTopicsStatus.topics ?? [] : [];
    const needle = topic.trim().toLowerCase();
    const filtered = needle ? all.filter((item) => item.toLowerCase().includes(needle)) : all;
    return filtered.slice(0, 50);
  }, [bookTopicsStatus, topic]);

  function pickTopic(value: string) {
    setTopic(value);
    setTopicFocused(false);
    setClarifyQuestion(null);
    setClarifyOptions([]);
    setShowCustomClarification(false);
    setCustomClarification("");
  }

  function changeSubject(value: string) {
    setSubject(value);
    resetLibrarySelection();
  }

  function changeGrade(value: string) {
    setGrade(value);
    resetLibrarySelection();
  }

  function buildTeacherContext(answers: AssistantAnswers, hasSource: boolean) {
    const framework = lessonFrameworkFor(lessonDesign.frameworkId);
    return [
      `Lesson goal: ${answers.goal ?? "explain"}`,
      `Student familiarity: ${answers.level ?? "some"}`,
      `Reference source: ${hasSource ? "uploaded source is primary; stay grounded in it" : "no uploaded source"}`,
      `Lesson design framework: ${framework.names.en}`,
      `Framework stages: ${framework.stages.join(" -> ")}`,
      `Framework guidance: ${framework.guidance}`,
      `Session duration: ${lessonDesign.duration}`,
      `Class size: ${lessonDesign.classSize || "not specified"}`,
      `Delivery mode: ${lessonDesign.deliveryMode}`,
      `Learner profile: ${lessonDesign.learnerProfile || "not specified"}`,
      `Existing objectives: ${lessonDesign.existingObjectives || "draft from the topic and source"}`,
      `Previously covered: ${lessonDesign.previouslyCovered || "not specified"}`,
      `Coming next: ${lessonDesign.comingNext || "not specified"}`,
      `Assumed prior knowledge: ${lessonDesign.priorKnowledge || "not specified"}`,
      `Assessment context: ${lessonDesign.assessmentContext || "not specified"}`,
      `GenAI policy: ${lessonDesign.aiPolicy}`,
    ].join("\n");
  }

  async function generateMaterial(
    finalTopic: string,
    sourceOverride: string | null = sourceText,
    answersOverride: AssistantAnswers = assistantAnswers,
  ) {
    setAssistantStep(null);
    setClarifyQuestion(null);
    setClarifyOptions([]);
    setShowCustomClarification(false);
    setCustomClarification("");
    setSubmitting(true);
    try {
      const res = await materialsApi.generateAll({
        topic: finalTopic,
        subject,
        language,
        grade,
        level: LEVELS[1],
        slide_count: slideCount,
        question_count: questionCount,
        test_type: testType,
        include_examples: includeExamples,
        source_text: sourceOverride || undefined,
        teacher_context: buildTeacherContext(answersOverride, Boolean(sourceOverride)),
        types: selected,
      });
      setResult(res);
      try {
        sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify({ topic: finalTopic, result: res }));
      } catch {
        // Session storage is optional.
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setSubmitting(false);
    }
  }

  async function selectLibraryBook(book: BookLibraryItem) {
    setLibrarySelecting(true);
    setError(null);
    try {
      const loaded = await bookApi.selectLibrary(book.id);
      setSelectedLibraryBook(book);
      setLibrarySource(loaded);
      setSourceFileName(book.title);
      setBookTopicsStatus(loaded.topics ?? null);
    } catch (err) {
      setSelectedLibraryBook(null);
      setLibrarySource(null);
      setBookTopicsStatus(null);
      setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      setLibrarySelecting(false);
    }
  }

  async function generateFromLibraryBook(answersOverride: AssistantAnswers) {
    if (!librarySource) {
      setError(t("common.error"));
      return;
    }
    setAssistantStep(null);
    setClarifyQuestion(null);
    setClarifyOptions([]);
    setShowCustomClarification(false);
    setCustomClarification("");
    setSubmitting(true);
    const controller = new AbortController();
    generationRef.current = controller;
    try {
      const res = await bookApi.generate({
        source_id: librarySource.id,
        scope: "all",
        topic,
        subject,
        language,
        grade,
        level: LEVELS[1],
        slide_count: slideCount,
        question_count: questionCount,
        test_type: testType,
        include_examples: includeExamples,
        teacher_context: `${buildTeacherContext(answersOverride, true)}\nSelected book: ${selectedLibraryBook?.title ?? "school textbook"}`,
        types: selected,
      }, controller.signal);
      setResult(res);
      try {
        sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify({ topic, result: res }));
      } catch {
        // Session storage is optional.
      }
    } catch (err) {
      if (!controller.signal.aborted) setError(err instanceof ApiError ? err.message : t("common.error"));
    } finally {
      if (generationRef.current === controller) generationRef.current = null;
      setSubmitting(false);
    }
  }

  function submit() {
    if (!topic.trim()) {
      setError(t("cur.topicRequired"));
      return;
    }
    if (selected.length === 0) {
      setError(t("create.pickAtLeastOne"));
      return;
    }
    if (!selectedLibraryBook || !librarySource) {
      setError(libraryCopy.required);
      return;
    }
    setError(null);
    void generateFromLibraryBook({ goal: "explain", level: "some", source: "library" });
  }

  function chooseClarification(option: string) {
    const clarifiedTopic = `${topic} — ${option}`;
    setTopic(clarifiedTopic);
    startAssistant(clarifiedTopic);
  }

  function skipClarification() {
    startAssistant(topic);
  }

  function submitCustomClarification() {
    const detail = customClarification.trim();
    if (!detail) return;
    chooseClarification(detail);
  }

  function startAssistant(nextTopic: string) {
    setTopic(nextTopic);
    setAssistantAnswers({});
    setAssistantStep(1);
    setClarifyQuestion(null);
    setClarifyOptions([]);
    setShowCustomClarification(false);
    setCustomClarification("");
    setSourceText(null);
    setSourceFileName(null);
    setPastedSourceText("");
    setSourceTruncated(false);
    setSelectedLibraryBook(null);
    setLibrarySource(null);
    setError(null);
  }

  function answerAssistant(key: "goal" | "level", value: string) {
    setAssistantAnswers((previous) => ({ ...previous, [key]: value }));
    setAssistantStep((previous) => (previous === 1 ? 2 : 3));
  }

  async function uploadAssistantSource(file: File) {
    setSourceUploading(true);
    setError(null);
    try {
      const uploaded = await materialsApi.uploadSource(file);
      if (!uploaded.text.trim()) {
        throw new ApiError(t("create.errorFile"));
      }
      setSourceText(uploaded.text);
      setSourceFileName(uploaded.filename || file.name);
      setSourceTruncated(uploaded.truncated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("create.errorFile"));
    } finally {
      setSourceUploading(false);
    }
  }

  function usePastedAssistantSource() {
    if (!pastedSourceText.trim()) {
      setError(t("create.errorFile"));
      return;
    }
    setSourceText(pastedSourceText.trim());
    setSourceFileName("Pasted lesson material");
    setSourceTruncated(false);
    finishAssistant("pasted", pastedSourceText.trim());
  }

  function finishAssistant(source: "library" | "uploaded" | "pasted" | "none", sourceOverride = sourceText) {
    const answers = { ...assistantAnswers, source };
    if (source === "library") {
      void generateFromLibraryBook(answers);
      return;
    }
    void generateMaterial(topic, source === "none" ? null : sourceOverride, answers);
  }

  async function downloadZip() {
    if (!result) return;
    setError(null);
    setZipping(true);
    try {
      await downloadAllZip({
        topic,
        language,
        konspekt: result.content.konspekt,
        test: result.content.test,
        prezentatsiya: result.content.prezentatsiya,
        lektsiya: result.content.lektsiya,
        amaliy: result.content.amaliy,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("cur.zipFailed"));
    } finally {
      setZipping(false);
    }
  }

  if (submitting) {
    return (
      <div className="mx-auto flex min-h-[min(72vh,46rem)] max-w-2xl items-center px-4 py-10 sm:px-6" role="status" aria-live="polite" aria-busy="true">
        <div className="w-full rounded-2xl border border-border-light bg-white p-5 shadow-[0_16px_45px_-28px_rgba(15,23,42,0.32)] sm:p-7">
          <div className="flex items-start gap-4">
            <div className="relative grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary">
              <span className="absolute inset-0 animate-ping rounded-xl bg-primary/10" />
              <Loader2 className="relative h-6 w-6 animate-spin" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{t("create.aiCreates")}</p>
              <h1 className="mt-1 text-xl font-bold text-text-primary sm:text-2xl">{t("create.generating")}</h1>
              <p className="mt-1 truncate text-sm text-text-secondary">{topic}</p>
            </div>
          </div>

          <div className="mt-7 grid gap-2 sm:grid-cols-2">
            {selected.map((type, index) => {
              const config = MATERIAL_TYPE_CONFIG[type];
              const Icon = config.icon;
              return (
                <div key={type} className="flex items-center gap-3 rounded-xl border border-border-light bg-surface-muted/60 px-3 py-3">
                  <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${config.bg}`}>
                    <Icon className={`h-4 w-4 ${config.color}`} />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-text-primary">
                    {t(MATERIAL_TYPE_LABEL_KEY[type])}
                  </span>
                  <span className="text-xs text-text-tertiary">{index + 1}/{selected.length}</span>
                </div>
              );
            })}
          </div>

          <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-surface-muted">
            <div className="h-full w-2/5 animate-pulse rounded-full bg-primary" />
          </div>
          <p className="mt-4 text-xs leading-5 text-text-tertiary">{t("create.generatingHint")}</p>
          <p className="mt-4 border-l-2 border-red-400 pl-3 text-xs leading-5 text-text-secondary">
            {t("create.aiWarning")}
          </p>
        </div>
      </div>
    );
  }
  if (assistantStep) {
    return (
      <CreationAssistant
        topic={topic}
        subject={subject}
        language={language}
        step={assistantStep}
        answers={assistantAnswers}
        sourceFileName={sourceFileName}
        pastedText={pastedSourceText}
        sourceTruncated={sourceTruncated}
        sourceUploading={sourceUploading}
        selectedLibraryBook={selectedLibraryBook}
        librarySelecting={librarySelecting}
        error={error}
        onAnswer={answerAssistant}
        onUploadSource={uploadAssistantSource}
        onSelectLibraryBook={(book) => void selectLibraryBook(book)}
        onPastedTextChange={setPastedSourceText}
        onUsePastedSource={usePastedAssistantSource}
        onFinish={finishAssistant}
        onBack={() => {
          setAssistantStep(null);
          setAssistantAnswers({});
          setSourceText(null);
          setSourceFileName(null);
          setSourceTruncated(false);
          setSelectedLibraryBook(null);
          setLibrarySource(null);
        }}
      />
    );
  }
  if (result) {
    const made = TYPES.filter((type) => result.content[type]);
    const failed = TYPES.filter((type) => !result.content[type] && selected.includes(type));
    return (
      <div className="relative mx-auto max-w-lg overflow-hidden px-4 pt-8 sm:px-6">
        <div
          className="pointer-events-none absolute -right-16 -top-16 -z-10 h-64 w-64 rounded-full bg-primary/[0.08] blur-3xl"
          aria-hidden
        />
        <div className="relative mb-6 overflow-hidden rounded-3xl border border-border-light bg-gradient-to-br from-primary-50/60 via-white to-white p-5 shadow-[0_4px_0_0_var(--color-border-light),0_20px_40px_-14px_rgba(220,38,38,0.12)] sm:p-7">
          <div className="relative flex items-center gap-3.5">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_3px_0_0_var(--color-primary-dark),0_10px_20px_-6px_rgba(220,38,38,0.4)]">
              <Check className="h-6 w-6" />
            </span>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{t("create.done")}</h1>
              <p className="text-sm text-text-secondary">«{topic}»</p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>
        )}

        {made.length > 1 && (
          <button
            onClick={downloadZip}
            disabled={zipping}
            className="mb-6 flex w-full items-center justify-center gap-2 rounded-xl border border-primary/20 bg-white py-2.5 text-sm font-semibold text-primary shadow-[0_3px_0_0_var(--color-primary-50),0_10px_20px_-8px_rgba(220,38,38,0.15)] transition-all duration-150 hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-60"
          >
            {zipping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {zipping ? t("cur.archiving") : t("cur.downloadZip")}
          </button>
        )}

        <div className="space-y-3">
          {made.map((type) => {
            const cfg = MATERIAL_TYPE_CONFIG[type];
            const id = result.ids?.[type];
            const Icon = cfg.icon;
            return (
              <button
                key={type}
                onClick={() => id && router.push(type === "prezentatsiya" ? `/dashboard/presentations/${id}/edit` : `/dashboard/materials/${type}/${id}`)}
                disabled={!id}
                className="flex w-full items-center gap-3 rounded-2xl border border-border-light bg-white p-4 text-left shadow-[0_2px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/20 hover:shadow-[0_3px_0_0_var(--color-primary-50),0_10px_20px_-10px_rgba(220,38,38,0.15)] disabled:pointer-events-none disabled:opacity-60"
              >
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${cfg.bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.8)]`}>
                  <Icon className={`h-5 w-5 ${cfg.color}`} />
                </span>
                <span className="flex-1 font-semibold text-text-primary">
                  {t(MATERIAL_TYPE_LABEL_KEY[type])}
                </span>
                <ArrowRight className="h-4 w-4 text-text-tertiary" />
              </button>
            );
          })}
        </div>

        {failed.length > 0 && (
          <p className="mt-4 rounded-xl bg-surface-muted px-4 py-3 text-xs text-text-secondary">
            {t("create.failedPrefix")} {failed.map((type) => t(MATERIAL_TYPE_LABEL_KEY[type])).join(", ")}.
            {" "}{t("create.failedSuffix")}
          </p>
        )}

        <button
          onClick={() => {
            setResult(null);
            setTopic("");
            try {
              sessionStorage.removeItem(RESULT_STORAGE_KEY);
            } catch {
              
            }
          }}
          className="mt-6 w-full rounded-xl border border-border bg-white py-3 text-sm font-semibold text-text-primary shadow-[0_3px_0_0_var(--color-border-light)] transition-all duration-150 hover:-translate-y-0.5"
        >
          {t("create.makeMore")}
        </button>
      </div>
    );
  }

  return (
    <div className="relative mx-auto max-w-2xl overflow-hidden px-4 pb-16 pt-8 sm:px-6">
      <div
        className="pointer-events-none absolute -right-20 -top-20 -z-10 h-72 w-72 rounded-full bg-primary/[0.07] blur-3xl"
        style={{ animation: "landing-blob-drift 20s ease-in-out infinite" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-16 top-60 -z-10 h-64 w-64 rounded-full bg-note-icon/[0.06] blur-3xl"
        style={{ animation: "landing-blob-drift 24s ease-in-out infinite", animationDelay: "-8s" }}
        aria-hidden
      />
      <div className="relative mb-6 overflow-hidden rounded-3xl border border-border-light bg-gradient-to-br from-primary-50/60 via-white to-white p-5 shadow-[0_4px_0_0_var(--color-border-light),0_20px_40px_-14px_rgba(220,38,38,0.12)] sm:p-7">
        <div
          className="pointer-events-none absolute -right-14 -top-14 h-48 w-48 rounded-full bg-primary/[0.08] blur-3xl"
          aria-hidden
        />
        <h1 className="relative text-2xl font-bold text-text-primary">{t("create.title")}</h1>
        <p className="relative mt-1 text-sm text-text-secondary">{t("create.prompt")}</p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">{t("create.gradeLabel")}</label>
          <select value={grade} onChange={(e) => changeGrade(e.target.value)} className={SELECT}>
            {CLASSES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">{t("create.subjectLabel")}</label>
            <select value={subject} onChange={(e) => changeSubject(e.target.value)} className={SELECT}>
            {SUBJECTS.map((s) => (
              <option key={s} value={s}>{SUBJECT_LABEL_KEYS[s] ? t(SUBJECT_LABEL_KEYS[s]) : s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">{t("create.languageLabel")}</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className={SELECT}>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>{LANGUAGE_LABEL_KEYS[l] ? t(LANGUAGE_LABEL_KEYS[l]) : l}</option>
            ))}
          </select>
        </div>
      </div>

      <section className="mb-6 rounded-2xl border border-primary/20 bg-gradient-to-br from-primary-50/60 via-white to-white p-4 shadow-[0_3px_0_0_var(--color-primary-50)] sm:p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-note-bg text-note-icon">
            <BookOpen className="h-5 w-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-bold text-text-primary">
              {libraryAutoFound ? libraryCopy.title : libraryCopy.pickTitle}
            </h2>
            <p className="mt-1 text-sm leading-5 text-text-secondary">
              {libraryLoading ? libraryCopy.loading : libraryAutoFound ? libraryCopy.foundHint : libraryCopy.hint}
            </p>
          </div>
          {libraryLoading && <Loader2 className="mt-1 h-4 w-4 animate-spin text-primary" />}
        </div>

        {!libraryLoading && libraryAutoFound && selectedLibraryBook && (
          <p className="mt-4 flex items-center gap-2 rounded-xl bg-white px-3 py-2.5 text-sm font-semibold text-text-primary">
            <Check className="h-4 w-4 shrink-0 text-emerald-600" />
            <span className="min-w-0 flex-1 whitespace-normal break-words">{selectedLibraryBook.title}</span>
          </p>
        )}

        {!libraryLoading && libraryAutoMissing && (
          <>
            {libraryBooks.length === 0 && (
              <p className="mt-4 rounded-xl bg-white px-3.5 py-3 text-sm text-text-secondary">{libraryCopy.empty}</p>
            )}
            {libraryBooks.length > 0 && (
              <div className="mt-4 space-y-2 pr-1">
                {libraryBooks.map((book) => {
                  const active = selectedLibraryBook?.id === book.id;
                  return (
                    <button
                      key={book.id}
                      type="button"
                      onClick={() => void selectLibraryBook(book)}
                      disabled={librarySelecting}
                      className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition disabled:pointer-events-none disabled:opacity-60 ${active ? "border-primary bg-white shadow-sm" : "border-border-light bg-white hover:border-primary/40 hover:bg-primary-50/30"}`}
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-note-bg text-note-icon">
                        <BookOpen className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block whitespace-normal break-words text-sm font-semibold leading-5 text-text-primary">{book.title}</span>
                        <span className="mt-0.5 block text-xs text-text-tertiary">{book.extension.toUpperCase()}{book.grade_hint ? ` · ${book.grade_hint}` : ""}</span>
                      </span>
                      {active ? <Check className="h-4 w-4 shrink-0 text-primary" /> : <ArrowRight className="h-4 w-4 shrink-0 text-text-tertiary" />}
                    </button>
                  );
                })}
              </div>
            )}
            {selectedLibraryBook && (
              <p className="mt-3 flex items-center gap-2 rounded-xl bg-white px-3 py-2.5 text-sm font-semibold text-text-primary">
                {librarySelecting ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Check className="h-4 w-4 text-emerald-600" />}
                <span className="min-w-0 flex-1 whitespace-normal break-words">{selectedLibraryBook.title}</span>
              </p>
            )}
          </>
        )}
      </section>

      <label className="mb-1.5 block text-sm font-semibold text-text-primary">{t("create.topicLabel")}</label>
      <div className="relative mb-1.5">
        <input
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value);
            setClarifyQuestion(null);
            setClarifyOptions([]);
            setShowCustomClarification(false);
            setCustomClarification("");
          }}
          onFocus={() => setTopicFocused(true)}
          onBlur={() => setTimeout(() => setTopicFocused(false), 150)}
          placeholder={t("create.topicPlaceholder")}
          className={`${FIELD} text-base`}
        />
        {topicFocused && topicSuggestions.length > 0 && (
          <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-xl border border-border bg-white py-1 shadow-lg">
            {topicSuggestions.map((item, index) => (
              <li key={index}>
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    pickTopic(item);
                  }}
                  className="block w-full whitespace-normal break-words px-4 py-2 text-left text-sm text-text-primary hover:bg-primary-50"
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {(bookTopicsStatus?.status === "pending" ||
        (bookTopicsStatus?.status === "ready" && (bookTopicsStatus.topics?.length ?? 0) > 0)) && (
        <p className="mb-1.5 text-xs text-text-tertiary">
          {bookTopicsStatus.status === "pending" ? t("create.topicLoadingHint") : t("create.topicFromBookHint")}
        </p>
      )}
      {librarySource && (
        <p className="mb-5 text-xs font-semibold text-red-600">{t("create.topicAccuracyHint")}</p>
      )}

      <div className="mb-6 grid gap-1.5">
        <label htmlFor="include-examples" className="text-sm font-semibold text-text-primary">
          {t("create.examplesLabel")}
        </label>
        <select
          id="include-examples"
          value={includeExamples ? "yes" : "no"}
          onChange={(e) => setIncludeExamples(e.target.value === "yes")}
          className={SELECT}
        >
          <option value="yes">{t("create.examplesYes")}</option>
          <option value="no">{t("create.examplesNo")}</option>
        </select>
      </div>

      <LessonDesignPanel
        language={language}
        value={lessonDesign}
        onChange={(key, value) => setLessonDesign((current) => ({ ...current, [key]: value }))}
      />

      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <label className="text-sm font-semibold text-text-primary">{t("create.whatToCreate")}</label>
        </div>
        <button
          type="button"
          onClick={() => setSelected(allChosen ? [] : [...TYPES])}
          className="text-xs font-semibold text-primary hover:text-primary-dark"
        >
          {allChosen ? t("create.deselectAll") : t("create.selectAll")}
        </button>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {TYPES.map((type) => {
          const cfg = MATERIAL_TYPE_CONFIG[type];
          const Icon = cfg.icon;
          const on = selected.includes(type);
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggle(type)}
              aria-pressed={on}
              className={`relative flex flex-col items-start gap-2.5 rounded-2xl border p-3.5 text-left transition-all duration-150 ${
                on
                  ? "border-primary bg-primary-50 shadow-[0_3px_0_0_var(--color-primary-50),0_12px_24px_-10px_rgba(220,38,38,0.25)]"
                  : `border-border-light ${CARD_BG[type]} shadow-[0_2px_0_0_var(--color-border-light)] hover:-translate-y-0.5 hover:border-border hover:shadow-[0_3px_0_0_var(--color-border-light),0_10px_20px_-10px_rgba(0,0,0,0.1)]`
              }`}
            >
              <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${cfg.bg} shadow-[inset_0_-2px_3px_rgba(0,0,0,0.08),inset_0_1px_1px_rgba(255,255,255,0.85)]`}>
                <Icon className={`h-6 w-6 ${cfg.color}`} />
              </span>
              <span className="text-sm font-semibold text-text-primary">
                {t(MATERIAL_TYPE_LABEL_KEY[type])}
              </span>
              {on && (
                <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_2px_0_0_var(--color-primary-dark)]">
                  <Check className="h-3 w-3" />
                </span>
              )}
            </button>
          );
        })}
      </div>

      {}
      {selected.includes("prezentatsiya") && (
        <CountPicker
          label={t("create.slideCount")}
          value={slideCount}
          onChange={setSlideCount}
        />
      )}
      {selected.includes("test") && (
        <>
          <CountPicker
            label={t("create.questionCount")}
            value={questionCount}
            onChange={setQuestionCount}
          />
          <div className="mb-5">
            <label className="mb-2 block text-sm font-semibold text-text-primary">
              {t("create.questionType")}
            </label>
            <div className="flex flex-wrap gap-2">
              {TEST_TYPES.map((tt) => (
                <button
                  key={tt.value}
                  type="button"
                  onClick={() => setTestType(tt.value)}
                  className={`rounded-xl border px-3.5 py-2 text-sm font-semibold transition-all duration-150 ${
                    testType === tt.value
                      ? "border-primary bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_3px_0_0_var(--color-primary-dark)]"
                      : "border-border bg-white text-text-primary hover:border-primary/40"
                  }`}
                >
                  {t(TEST_TYPE_LABEL_KEYS[tt.value])}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {clarifyQuestion && (
        <div className="mb-4 rounded-xl border border-primary/20 bg-primary-50 p-4" role="dialog" aria-live="polite">
          <div className="flex items-start gap-3">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white text-primary">
              <Sparkles className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold leading-5 text-text-primary">{clarifyQuestion}</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {clarifyOptions.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => chooseClarification(option)}
                    className="rounded-lg border border-border bg-white px-3 py-2.5 text-left text-sm font-medium text-text-primary transition hover:border-primary/40 hover:bg-primary-50"
                  >
                    {option}
                  </button>
                ))}
              </div>
              {showCustomClarification ? (
                <form
                  className="mt-3 flex flex-col gap-2 sm:flex-row"
                  onSubmit={(event) => {
                    event.preventDefault();
                    submitCustomClarification();
                  }}
                >
                  <input
                    value={customClarification}
                    onChange={(event) => setCustomClarification(event.target.value)}
                    autoFocus
                    placeholder={t("create.clarifyAnswerPlaceholder")}
                    className="min-w-0 flex-1 rounded-lg border border-border bg-white px-3 py-2.5 text-sm text-text-primary outline-none focus:border-primary focus:ring-4 focus:ring-primary/10"
                  />
                  <button
                    type="submit"
                    disabled={!customClarification.trim()}
                    className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-primary-dark disabled:pointer-events-none disabled:opacity-50"
                  >
                    {t("create.clarifyContinue")}
                  </button>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => setShowCustomClarification(true)}
                  className="mt-3 text-xs font-semibold text-primary underline-offset-2 hover:text-primary-dark hover:underline"
                >
                  {t("create.clarifyOwn")}
                </button>
              )}
              <button
                type="button"
                onClick={skipClarification}
                className="ml-4 mt-3 text-xs font-medium text-text-secondary underline-offset-2 hover:text-text-primary hover:underline"
              >
                {t("create.clarifySkip")}
              </button>
            </div>
          </div>
        </div>
      )}

      {!clarifyQuestion && <button
        onClick={submit}
        disabled={!topic.trim() || selected.length === 0 || !librarySource || librarySelecting}
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary py-3.5 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_12px_24px_-6px_rgba(220,38,38,0.4)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_16px_28px_-6px_rgba(220,38,38,0.45)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4" />
        {selected.length === 1
          ? `${t("create.submit")} ${t(MATERIAL_TYPE_LABEL_KEY[selected[0]]).toLowerCase()}`
          : `${t("create.submit")} ${selected.length}`}
      </button>
      }
    </div>

  );
}


function CountPicker({
  label, value, onChange,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
}) {
  const t = useT();
  const custom = !COUNT_PRESETS.includes(value);
  return (
    <div className="mb-5">
      <label className="mb-2 block text-sm font-semibold text-text-primary">{label}</label>
      <div className="flex flex-wrap items-center gap-2">
        {COUNT_PRESETS.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`min-w-[3.5rem] rounded-xl border px-4 py-2 text-sm font-semibold transition-all duration-150 ${
              value === n
                ? "border-primary bg-gradient-to-b from-primary-light to-primary text-white shadow-[0_3px_0_0_var(--color-primary-dark)]"
                : "border-border bg-white text-text-primary hover:border-primary/40"
            }`}
          >
            {n}
          </button>
        ))}
        <input
          type="number"
          min={1}
          max={60}
          value={custom ? value : ""}
          onChange={(e) => {
            const n = Number(e.target.value);
            
            
            
            if (Number.isFinite(n) && n > 0) onChange(Math.min(60, Math.round(n)));
          }}
          placeholder={t("create.custom")}
          className={`w-24 rounded-xl border px-3 py-2 text-sm outline-none transition ${
            custom ? "border-primary bg-primary-50 text-text-primary" : "border-border bg-white"
          }`}
        />
      </div>
    </div>
  );
}
