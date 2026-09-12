"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Copy,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { materialsApi, ApiError } from "@/lib/api";

// The four question shapes the generator produces and TestPlayer can grade
// (see backend/app/ai_service.py's _QUESTION_TYPE_INFO). The editor has to
// understand all four, because a test is a heterogeneous list: one item's
// answer lives in `correct_index`, the next one's in `correct_indices`,
// the third's in `model_answer`. Editing them through a single "correct
// answer" field would silently corrupt three of the four.
type QuestionType = "multiple_choice" | "true_false" | "multiple_select" | "open_ended";

interface Question {
  question: string;
  type?: QuestionType;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
  difficulty?: string;
  image_query?: string;
  image?: string;
}

const TYPE_LABELS: Record<QuestionType, string> = {
  multiple_choice: "Один правильный ответ",
  true_false: "Верно / Неверно",
  multiple_select: "Несколько правильных",
  open_ended: "Развёрнутый ответ",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "Лёгкий",
  medium: "Средний",
  hard: "Сложный",
};
const DIFFICULTIES = ["easy", "medium", "hard"];

function normalizedType(q: Question): QuestionType {
  return (q.type as QuestionType) ?? "multiple_choice";
}

/** Teacher/administrator editor for a generated test.
 *
 * A separate route rather than another mode inside the shared material
 * viewer for the same reason the slide editor is one: this needs a full
 * page of its own, and threading it through the page that six material
 * types share would mean a lot of `type === "test"` branching for a
 * layout only one type wants.
 *
 * Saving goes through the same PUT /materials/tests/{id} the rest of the
 * app already uses, so the ownership check that endpoint performs is the
 * only thing that decides whether an edit is allowed — nothing here
 * grants anything.
 */
export default function TestEditorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const [item, setItem] = useState<{ subject: string; grade: string } | null>(null);
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [open, setOpen] = useState<number | null>(0);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    materialsApi
      .get("test", id)
      .then((loaded) => {
        setItem({ subject: loaded.subject, grade: loaded.grade });
        setTitle(loaded.title);
        try {
          setContent(JSON.parse(loaded.questions_json ?? "{}"));
        } catch {
          setContent({});
        }
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Не удалось загрузить тест"));
  }, [id]);

  const questions = useMemo(() => (content.questions as Question[] | undefined) ?? [], [content]);

  // Debounced autosave with the FULL next state — questions_json holds the
  // whole blob, so a partial patch is not expressible (same contract the
  // presentation editor works under). The title is a real column, so it
  // travels alongside rather than inside the JSON.
  function persist(nextContent: Record<string, unknown>, nextTitle = title) {
    setContent(nextContent);
    setSaveState("saving");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      try {
        await materialsApi.update("test", id, {
          title: nextTitle,
          questions_json: JSON.stringify({ ...nextContent, title: nextTitle }),
        });
        setSaveState("saved");
      } catch {
        setSaveState("idle");
      }
    }, 700);
  }

  function updateQuestions(next: Question[]) {
    persist({ ...content, questions: next });
  }

  function updateQuestion(index: number, patch: Partial<Question>) {
    updateQuestions(questions.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  /** Switching type has to rewrite the answer fields, not just the label.
   * A true/false question with four leftover options, or a
   * multiple_select still carrying a single `correct_index`, is exactly
   * the shape TestPlayer's grader mis-scores — so the conversion builds
   * the target shape explicitly and drops what no longer applies. */
  function changeType(index: number, type: QuestionType) {
    const q = questions[index];
    const base: Question = {
      question: q.question,
      type,
      explanation: q.explanation,
      difficulty: q.difficulty,
    };
    if (type === "true_false") {
      updateQuestion(index, {
        ...base,
        options: ["Верно", "Неверно"],
        correct_index: q.correct_index === 1 ? 1 : 0,
        correct_indices: undefined,
        model_answer: undefined,
      });
    } else if (type === "multiple_select") {
      const options = q.options?.length ? q.options : ["", "", "", ""];
      updateQuestion(index, {
        ...base,
        options,
        correct_indices: q.correct_indices ?? (q.correct_index !== undefined ? [q.correct_index] : []),
        correct_index: undefined,
        model_answer: undefined,
      });
    } else if (type === "open_ended") {
      updateQuestion(index, {
        ...base,
        options: undefined,
        correct_index: undefined,
        correct_indices: undefined,
        model_answer: q.model_answer ?? "",
      });
    } else {
      const options = q.options?.length ? q.options : ["", "", "", ""];
      updateQuestion(index, {
        ...base,
        options,
        correct_index: q.correct_index ?? q.correct_indices?.[0] ?? 0,
        correct_indices: undefined,
        model_answer: undefined,
      });
    }
  }

  function moveQuestion(index: number, dir: -1 | 1) {
    const target = index + dir;
    if (target < 0 || target >= questions.length) return;
    const next = [...questions];
    [next[index], next[target]] = [next[target], next[index]];
    updateQuestions(next);
    setOpen(target);
  }

  function removeQuestion(index: number) {
    if (!confirm("Удалить этот вопрос?")) return;
    updateQuestions(questions.filter((_, i) => i !== index));
    setOpen(null);
  }

  function duplicateQuestion(index: number) {
    const next = [...questions];
    next.splice(index + 1, 0, JSON.parse(JSON.stringify(questions[index])));
    updateQuestions(next);
    setOpen(index + 1);
  }

  function addQuestion() {
    const next: Question[] = [
      ...questions,
      {
        question: "",
        type: "multiple_choice",
        options: ["", "", "", ""],
        correct_index: 0,
        explanation: "",
        difficulty: "medium",
      },
    ];
    updateQuestions(next);
    setOpen(next.length - 1);
  }

  /** Removing an option has to renumber whatever pointed at the ones after
   * it. Dropping option 1 of four leaves the old `correct_index: 2`
   * pointing at what is now option 3 — a silently wrong answer key, and
   * the kind of bug nobody notices until a pupil is marked down for a
   * right answer. */
  function removeOption(index: number, optionIndex: number) {
    const q = questions[index];
    const options = (q.options ?? []).filter((_, i) => i !== optionIndex);
    const patch: Partial<Question> = { options };
    if (q.correct_index !== undefined) {
      patch.correct_index =
        q.correct_index === optionIndex
          ? 0
          : q.correct_index > optionIndex
            ? q.correct_index - 1
            : q.correct_index;
    }
    if (q.correct_indices) {
      patch.correct_indices = q.correct_indices
        .filter((i) => i !== optionIndex)
        .map((i) => (i > optionIndex ? i - 1 : i));
    }
    updateQuestion(index, patch);
  }

  if (error) {
    return <div className="px-4 pt-10 text-center text-sm text-primary-dark">{error}</div>;
  }
  if (!item) {
    return <div className="px-4 pt-10 text-center text-sm text-text-secondary">Загрузка...</div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-4 pb-16 pt-6 sm:px-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
        <button
          onClick={() => router.push(`/dashboard/materials/test/${id}`)}
          className="flex items-center gap-1.5 text-sm font-medium text-text-secondary"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад
        </button>
        <div className="flex items-center gap-2 text-xs text-text-tertiary">
          {saveState === "saving" && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" /> Сохранение…
            </span>
          )}
          {saveState === "saved" && <span>Сохранено</span>}
        </div>
      </div>

      {/* Title + topic. Both are real columns on the row, not part of the
          questions blob, so they save through the same PUT but as their
          own fields. */}
      <div className="mb-4 space-y-3 rounded-2xl border border-border-light bg-surface p-4">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-text-tertiary">
            Название теста
          </label>
          <input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              persist(content, e.target.value);
            }}
            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm font-semibold text-text-primary outline-none focus:border-primary/50"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-text-tertiary">
            Тема
          </label>
          <input
            value={(content.description as string | undefined) ?? ""}
            onChange={(e) => persist({ ...content, description: e.target.value })}
            placeholder="О чём этот тест"
            className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50"
          />
          <p className="mt-1 text-xs text-text-tertiary">
            {item.subject} • {item.grade} • {questions.length} вопр.
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {questions.map((q, i) => {
          const type = normalizedType(q);
          const isOpen = open === i;
          return (
            <div key={i} className="overflow-hidden rounded-2xl border border-border-light bg-surface">
              <div className="flex items-start gap-2 p-3">
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="flex min-w-0 flex-1 items-start gap-2.5 text-left"
                >
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-xs font-bold text-primary">
                    {i + 1}
                  </span>
                  <span className="min-w-0 break-words text-sm text-text-primary">
                    {q.question || <span className="text-text-tertiary">Без текста</span>}
                  </span>
                </button>
                {/* Always visible, never hover-revealed: this page is used
                    on a phone as much as a laptop, and a hover-only control
                    does not exist on a touch screen. */}
                <div className="flex shrink-0 items-center gap-0.5">
                  <button
                    onClick={() => moveQuestion(i, -1)}
                    disabled={i === 0}
                    title="Выше"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text-tertiary hover:bg-surface-muted hover:text-text-primary disabled:opacity-30"
                  >
                    <ChevronUp className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => moveQuestion(i, 1)}
                    disabled={i === questions.length - 1}
                    title="Ниже"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text-tertiary hover:bg-surface-muted hover:text-text-primary disabled:opacity-30"
                  >
                    <ChevronDown className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => duplicateQuestion(i)}
                    title="Дублировать"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text-tertiary hover:bg-surface-muted hover:text-text-primary"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => removeQuestion(i)}
                    title="Удалить"
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-text-tertiary hover:bg-primary-50 hover:text-primary-dark"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {isOpen && (
                <div className="space-y-3 border-t border-border-light bg-surface-muted/40 p-3">
                  <textarea
                    value={q.question}
                    onChange={(e) => updateQuestion(i, { question: e.target.value })}
                    rows={2}
                    placeholder="Текст вопроса"
                    className="w-full resize-y rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50"
                  />

                  <div className="flex flex-wrap gap-2">
                    <label className="min-w-0 flex-1">
                      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
                        Тип
                      </span>
                      <select
                        value={type}
                        onChange={(e) => changeType(i, e.target.value as QuestionType)}
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50"
                      >
                        {(Object.keys(TYPE_LABELS) as QuestionType[]).map((k) => (
                          <option key={k} value={k}>
                            {TYPE_LABELS[k]}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="min-w-0 flex-1">
                      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
                        Сложность
                      </span>
                      <select
                        value={q.difficulty ?? "medium"}
                        onChange={(e) => updateQuestion(i, { difficulty: e.target.value })}
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50"
                      >
                        {DIFFICULTIES.map((d) => (
                          <option key={d} value={d}>
                            {DIFFICULTY_LABELS[d]}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  {type === "open_ended" ? (
                    <div>
                      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
                        Образец ответа
                      </span>
                      <textarea
                        value={q.model_answer ?? ""}
                        onChange={(e) => updateQuestion(i, { model_answer: e.target.value })}
                        rows={3}
                        className="w-full resize-y rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50"
                      />
                    </div>
                  ) : (
                    <div>
                      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
                        Варианты — отметьте правильный
                      </span>
                      <div className="space-y-1.5">
                        {(q.options ?? []).map((opt, j) => {
                          const checked =
                            type === "multiple_select"
                              ? (q.correct_indices ?? []).includes(j)
                              : q.correct_index === j;
                          return (
                            <div key={j} className="flex items-center gap-2">
                              <input
                                type={type === "multiple_select" ? "checkbox" : "radio"}
                                name={`correct-${i}`}
                                checked={checked}
                                onChange={() => {
                                  if (type === "multiple_select") {
                                    const cur = q.correct_indices ?? [];
                                    updateQuestion(i, {
                                      correct_indices: checked
                                        ? cur.filter((x) => x !== j)
                                        : [...cur, j].sort((a, b) => a - b),
                                    });
                                  } else {
                                    updateQuestion(i, { correct_index: j });
                                  }
                                }}
                                className="h-4 w-4 shrink-0 accent-[var(--color-primary)]"
                              />
                              <input
                                value={opt}
                                onChange={(e) => {
                                  const next = [...(q.options ?? [])];
                                  next[j] = e.target.value;
                                  updateQuestion(i, { options: next });
                                }}
                                disabled={type === "true_false"}
                                className="min-w-0 flex-1 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-primary/50 disabled:bg-surface-muted disabled:text-text-secondary"
                              />
                              {type !== "true_false" && (q.options?.length ?? 0) > 2 && (
                                <button
                                  onClick={() => removeOption(i, j)}
                                  title="Удалить вариант"
                                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-text-tertiary hover:text-primary-dark"
                                >
                                  <X className="h-4 w-4" />
                                </button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      {type !== "true_false" && (
                        <button
                          onClick={() =>
                            updateQuestion(i, { options: [...(q.options ?? []), ""] })
                          }
                          className="mt-2 flex items-center gap-1 text-xs font-medium text-text-tertiary hover:text-primary"
                        >
                          <Plus className="h-3 w-3" /> Добавить вариант
                        </button>
                      )}
                    </div>
                  )}

                  <div>
                    <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-text-tertiary">
                      Пояснение
                    </span>
                    <textarea
                      value={q.explanation ?? ""}
                      onChange={(e) => updateQuestion(i, { explanation: e.target.value })}
                      rows={2}
                      placeholder="Почему этот ответ правильный"
                      className="w-full resize-y rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-secondary outline-none focus:border-primary/50"
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <button
        onClick={addQuestion}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-border py-3 text-sm font-medium text-text-secondary transition hover:border-primary hover:text-primary"
      >
        <Plus className="h-4 w-4" />
        Добавить вопрос
      </button>
    </div>
  );
}
