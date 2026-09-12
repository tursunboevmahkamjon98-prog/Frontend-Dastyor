"use client";

import { useEffect, useMemo, useState } from "react";
import { X, Play, ListChecks, Timer, CheckCircle2, XCircle, RotateCw, Loader2, History } from "lucide-react";
import { materialsApi, TestAttemptOut } from "@/lib/api";
import { Confetti, Burst } from "./game/effects";
import { sfx } from "./game/sound";
import MathText from "./konspekt/MathText";
import { useT, useLocale } from "@/lib/i18n";

// Intl locale for attempt-history timestamps — mirrors useLocale()'s "ru" |
// "tg" | "en" onto a real BCP-47 tag for toLocaleString.
const DATE_LOCALE: Record<string, string> = { ru: "ru-RU", tg: "tg-TJ", en: "en-US" };

interface Question {
  question: string;
  type?: string;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
}

type Given = number | number[] | string | null;

interface Answer {
  index: number;
  type: string;
  given: Given;
  // true/false for auto-gradable questions, null for open_ended (no
  // reliable auto-grader — kept for the pupil's own review only).
  correct: boolean | null;
  timedOut?: boolean;
}

// Rendered as "{n} {t('test.seconds')}" per option — only the seconds unit
// and the "no limit" choice need translating, not six separate strings.
const SECONDS_OPTIONS = [15, 30, 45, 60, 90, 120];

/** Entry point for playing a "test" material online — mounted by the
 * material viewer (dashboard/materials/[type]/[id]) as a "Пройти тест"
 * card, same slot GamePlayer occupies for "igra". Two states: an inline
 * cover card in the page's normal layout (question count, per-question
 * time limit the teacher can change, and past-attempt history), and, once
 * launched, a fixed full-viewport TestRunner — a real quiz screen, not a
 * widget in the site chrome, matching GamePlayer's overlay pattern.
 *
 * Unlike GamePlayer, there's no local content-reroll here: a test's
 * questions are graded content (correct_index/explanation), not something
 * a pupil should get a fresh random set of mid-review — regenerating
 * lives in the material page's own AI chat-edit box instead. */
export default function TestPlayer({
  content,
  materialId,
  initialTimeLimit,
  autoStart = false,
  onExit,
}: {
  content: Record<string, unknown>;
  materialId: string;
  /** From MaterialOut.time_limit_seconds — a real DB column on Test, not
   * part of the questions_json blob `content` holds, so it's passed in
   * separately rather than read off `content`. */
  initialTimeLimit?: number | null;
  /** Skip the cover card and open the quiz straight away.
   *
   * The cover exists for the teacher looking at their own material: it
   * carries the per-question time limit they set and their past attempts.
   * The dedicated pupil route (/dashboard/tests/[id]/play) is a link they
   * hand to a pupil to SIT the test — a settings panel and a history of
   * someone else's scores are the wrong first screen there, and the time
   * limit in particular is not a pupil's to change. */
  autoStart?: boolean;
  /** Where "close" goes when there is no cover card to fall back to —
   * the play route navigates instead of unmounting an overlay. */
  onExit?: () => void;
}) {
  const t = useT();
  const { locale } = useLocale();
  const [launched, setLaunched] = useState(autoStart);
  const [timeLimit, setTimeLimit] = useState<number | null>(initialTimeLimit ?? null);
  const [savingLimit, setSavingLimit] = useState(false);
  const [history, setHistory] = useState<TestAttemptOut[] | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const title = (content.title as string | undefined) ?? t("test.defaultTitle");
  const questions = useMemo(
    () => ((content.questions as Question[] | undefined) ?? []).filter((q) => q && q.question),
    [content]
  );

  async function toggleHistory() {
    const opening = !historyOpen;
    setHistoryOpen(opening);
    if (opening && history === null) {
      try {
        setHistory(await materialsApi.listTestAttempts(materialId));
      } catch {
        setHistory([]);
      }
    }
  }

  async function changeLimit(value: number | null) {
    setSavingLimit(true);
    try {
      await materialsApi.update("test", materialId, { time_limit_seconds: value });
      setTimeLimit(value);
    } finally {
      setSavingLimit(false);
    }
  }

  if (questions.length === 0) {
    return <p className="text-sm text-text-secondary">{t("test.noQuestions")}</p>;
  }

  return (
    <>
      {!autoStart && (
      <div className="mb-6 rounded-2xl border border-border-light bg-surface p-5">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary-50">
            <ListChecks className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm font-bold text-text-primary">{title}</p>
            <p className="text-xs text-text-secondary">
              {questions.length} {t("test.questionsCount")}
            </p>
          </div>
        </div>

        <div className="mb-4 flex items-center gap-2 text-xs text-text-secondary">
          <Timer className="h-3.5 w-3.5 shrink-0" />
          <span className="shrink-0">{t("test.timePerQuestion")}</span>
          <select
            value={timeLimit ?? ""}
            disabled={savingLimit}
            onChange={(e) => changeLimit(e.target.value ? Number(e.target.value) : null)}
            className="rounded-lg border border-border bg-surface px-2 py-1 text-xs font-medium text-text-primary outline-none disabled:opacity-60"
          >
            <option value="">{t("test.timeUnlimited")}</option>
            {SECONDS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s} {t("test.seconds")}
              </option>
            ))}
          </select>
          {savingLimit && <Loader2 className="h-3 w-3 animate-spin text-text-tertiary" />}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setLaunched(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 transition hover:bg-primary-dark"
          >
            <Play className="h-4 w-4 fill-current" />
            {t("test.play")}
          </button>
          <button
            onClick={toggleHistory}
            className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3.5 py-2.5 text-sm font-medium text-text-primary hover:bg-surface-muted"
          >
            <History className="h-4 w-4" />
            {t("test.results")}
          </button>
        </div>

        {historyOpen && (
          <div className="mt-3 space-y-1.5 border-t border-border-light pt-3">
            {history === null && <p className="text-xs text-text-tertiary">{t("test.loading")}</p>}
            {history?.length === 0 && <p className="text-xs text-text-tertiary">{t("test.noAttemptsYet")}</p>}
            {history?.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-lg bg-surface-muted px-3 py-1.5 text-xs">
                <span className="text-text-secondary">
                  {new Date(a.created_at).toLocaleString(DATE_LOCALE[locale] ?? "ru-RU", {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="font-semibold text-text-primary">
                  {a.total > 0 ? `${a.score}/${a.total}` : t("test.noScore")}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      )}

      {launched && (
        <div className="fixed inset-0 z-[200] overflow-y-auto bg-[#fff7f5]">
          {/* Ambient background — soft drifting blobs in the brand color,
              same "real screen, not a widget" treatment GamePlayer's dark
              overlay uses, just toned for this light/red theme instead. */}
          <div className="pointer-events-none fixed inset-0 overflow-hidden">
            <div
              className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-primary/10 blur-3xl"
              style={{ animation: "game-float 9s ease-in-out infinite" }}
            />
            <div
              className="absolute -bottom-32 -right-16 h-80 w-80 rounded-full bg-primary/10 blur-3xl"
              style={{ animation: "game-float 11s ease-in-out infinite reverse" }}
            />
          </div>
          <TestRunner
            t={t}
            questions={questions}
            timeLimitSeconds={timeLimit}
            materialId={materialId}
            onClose={() => {
              if (onExit) {
                onExit();
                return;
              }
              setLaunched(false);
              setHistory(null);
              setHistoryOpen(false);
            }}
          />
        </div>
      )}
    </>
  );
}

function isAutoGraded(type: string | undefined): boolean {
  return type !== "open_ended";
}

function gradeSelection(q: Question, selected: number[]): boolean {
  if (q.type === "multiple_select") {
    const correctSet = new Set(q.correct_indices ?? []);
    const givenSet = new Set(selected);
    return correctSet.size === givenSet.size && [...correctSet].every((i) => givenSet.has(i));
  }
  return selected[0] === q.correct_index;
}

function TestRunner({
  t,
  questions,
  timeLimitSeconds,
  materialId,
  onClose,
}: {
  t: ReturnType<typeof useT>;
  questions: Question[];
  timeLimitSeconds: number | null;
  materialId: string;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<"question" | "feedback" | "result">("question");
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [openText, setOpenText] = useState("");
  const [timeLeft, setTimeLeft] = useState<number | null>(timeLimitSeconds);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const total = questions.length;
  const q = questions[index];
  const lastAnswer = answers[answers.length - 1];

  // Fresh answer state (and a restarted timer) every time the question changes.
  useEffect(() => {
    setSelected([]);
    setOpenText("");
    setTimeLeft(timeLimitSeconds);
  }, [index, timeLimitSeconds]);

  // Per-question countdown — only runs while a question is actually being
  // answered (not during feedback/result), and only when the teacher set a
  // limit at all.
  useEffect(() => {
    if (phase !== "question" || timeLeft === null) return;
    if (timeLeft <= 0) {
      commitAnswer(isAutoGraded(q.type) ? (q.type === "multiple_select" ? [] : null) : openText.trim() || null, isAutoGraded(q.type) ? false : null, true);
      return;
    }
    const timer = setTimeout(() => setTimeLeft((v) => (v === null ? null : v - 1)), 1000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, timeLeft]);

  function commitAnswer(given: Given, correct: boolean | null, timedOut = false) {
    setAnswers((prev) => [...prev, { index, type: q.type ?? "multiple_choice", given, correct, timedOut }]);
    if (correct === true) sfx.correct();
    else if (correct === false) sfx.wrong();
    setPhase("feedback");
  }

  function toggleOption(i: number) {
    if (q.type === "multiple_select") {
      setSelected((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]));
    } else {
      setSelected([i]);
    }
  }

  function submitAnswer() {
    if (q.type === "open_ended") {
      commitAnswer(openText.trim() || null, null);
      return;
    }
    if (selected.length === 0) return;
    commitAnswer(q.type === "multiple_select" ? selected : selected[0], gradeSelection(q, selected));
  }

  async function next() {
    if (index + 1 < total) {
      setIndex((v) => v + 1);
      setPhase("question");
    } else {
      await finish();
    }
  }

  async function finish() {
    setPhase("result");
    const gradable = answers.filter((a) => a.correct !== null);
    const score = gradable.filter((a) => a.correct).length;
    const totalGraded = gradable.length;
    setSaveState("saving");
    try {
      await materialsApi.submitTestAttempt(materialId, {
        score,
        total: totalGraded,
        answers_json: JSON.stringify(answers),
      });
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  function restart() {
    setIndex(0);
    setAnswers([]);
    setPhase("question");
    setSaveState("idle");
  }

  if (phase === "result") {
    const gradable = answers.filter((a) => a.correct !== null);
    const score = gradable.filter((a) => a.correct).length;
    const totalGraded = gradable.length;
    const ratio = totalGraded > 0 ? score / totalGraded : 0;
    const good = totalGraded > 0 && ratio >= 0.6;
    const pct = Math.round(ratio * 100);
    const scoreRingRadius = 42;
    const scoreRingCirc = 2 * Math.PI * scoreRingRadius;
    return (
      <div className="relative flex min-h-screen items-center justify-center p-4">
        {good && <Confetti count={44} />}
        <div
          className="relative w-full max-w-sm rounded-3xl border border-border-light bg-surface p-6 text-center shadow-xl shadow-primary/10"
          style={{ animation: "game-round-in 0.4s ease-out" }}
        >
          <button onClick={onClose} className="absolute right-4 top-4 text-text-tertiary hover:text-text-primary">
            <X className="h-5 w-5" />
          </button>

          {totalGraded > 0 ? (
            <div className="relative mx-auto mb-4 h-24 w-24">
              <svg viewBox="0 0 96 96" className="h-24 w-24 -rotate-90">
                <circle cx="48" cy="48" r={scoreRingRadius} fill="none" strokeWidth="7" className="stroke-surface-muted" />
                <circle
                  cx="48"
                  cy="48"
                  r={scoreRingRadius}
                  fill="none"
                  strokeWidth="7"
                  strokeLinecap="round"
                  strokeDasharray={scoreRingCirc}
                  strokeDashoffset={scoreRingCirc * (1 - ratio)}
                  className={good ? "stroke-primary" : "stroke-text-tertiary"}
                  style={{ transition: "stroke-dashoffset 1s ease-out" }}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                {good ? <CheckCircle2 className="h-6 w-6 text-primary" /> : <ListChecks className="h-6 w-6 text-text-tertiary" />}
              </div>
            </div>
          ) : (
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-surface-muted">
              <ListChecks className="h-8 w-8 text-text-tertiary" />
            </div>
          )}

          <h3 className="text-lg font-extrabold text-text-primary">{t("test.finished")}</h3>
          <p className="mt-1 text-3xl font-black text-primary" style={{ animation: "game-pop 0.5s ease-out 0.4s both" }}>
            {totalGraded > 0 ? `${score}/${totalGraded}` : "—"}
          </p>
          {totalGraded > 0 && (
            <p className="mt-1 text-xs text-text-secondary">
              {pct}
              {t("test.percentCorrect")}
            </p>
          )}
          {questions.some((qq) => qq.type === "open_ended") && (
            <p className="mt-2 text-[11px] text-text-tertiary">{t("test.openEndedHint")}</p>
          )}

          <p className="mt-3 text-[11px] text-text-tertiary">
            {saveState === "saving" && t("test.saving")}
            {saveState === "saved" && t("test.saved")}
            {saveState === "error" && t("test.saveFailed")}
          </p>

          <div className="mt-5 flex gap-2">
            <button
              onClick={restart}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-semibold text-text-primary hover:bg-surface-muted"
            >
              <RotateCw className="h-4 w-4" />
              {t("test.restart")}
            </button>
            <button
              onClick={onClose}
              className="flex-1 rounded-xl bg-primary py-2.5 text-sm font-semibold text-white shadow-sm shadow-primary/25 hover:bg-primary-dark"
            >
              {t("test.close")}
            </button>
          </div>
        </div>
      </div>
    );
  }

  const showingFeedback = phase === "feedback";
  const answerForFeedback = showingFeedback ? lastAnswer : null;
  const urgent = timeLeft !== null && timeLeft <= 5 && phase === "question";
  // Ring geometry for the circular countdown — see the <svg> below.
  const ringRadius = 15;
  const ringCirc = 2 * Math.PI * ringRadius;
  const ringFrac = timeLeft !== null && timeLimitSeconds ? Math.max(0, timeLeft) / timeLimitSeconds : 1;

  return (
    <div className="relative mx-auto flex min-h-screen max-w-lg flex-col p-4">
      <div className="mb-5 flex items-center justify-between">
        <button
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-surface/80 text-text-tertiary shadow-sm backdrop-blur-sm transition hover:bg-surface hover:text-text-primary"
        >
          <X className="h-4.5 w-4.5" />
        </button>
        <p className="rounded-full bg-surface/80 px-3 py-1 text-xs font-bold text-text-secondary shadow-sm backdrop-blur-sm">
          {index + 1} <span className="text-text-tertiary">/ {total}</span>
        </p>
        {timeLeft !== null && phase === "question" ? (
          <div className="relative flex h-9 w-9 items-center justify-center">
            <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
              <circle cx="18" cy="18" r={ringRadius} fill="none" strokeWidth="3" className="stroke-surface-muted" />
              <circle
                cx="18"
                cy="18"
                r={ringRadius}
                fill="none"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={ringCirc}
                strokeDashoffset={ringCirc * (1 - ringFrac)}
                className={`transition-[stroke-dashoffset] duration-1000 ease-linear ${urgent ? "stroke-primary" : "stroke-primary/70"}`}
              />
            </svg>
            <span
              className={`text-[11px] font-black ${urgent ? "text-primary" : "text-text-secondary"}`}
              style={urgent ? { animation: "game-pop 0.9s ease-in-out infinite" } : undefined}
            >
              {timeLeft}
            </span>
          </div>
        ) : (
          <span className="w-9" />
        )}
      </div>

      {/* Segmented progress — one pill per question, filled as answered,
          the current one a taller highlighted bar, matching Duolingo-style
          quiz progress rather than one plain continuous bar. */}
      <div className="mb-5 flex gap-1">
        {questions.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i < index || (i === index && showingFeedback)
                ? "bg-primary"
                : i === index
                ? "bg-primary/40"
                : "bg-surface-muted"
            }`}
          />
        ))}
      </div>

      <div
        key={index}
        className={`relative flex-1 overflow-hidden rounded-3xl border border-border-light bg-surface p-5 shadow-lg shadow-primary/5 ${
          answerForFeedback?.correct === false ? "animate-[game-shake_0.5s_ease-in-out]" : ""
        }`}
        style={{ animation: answerForFeedback?.correct === false ? undefined : "game-round-in 0.35s ease-out" }}
      >
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary/60 via-primary to-primary/60" />

        <p className="mb-4 text-base font-bold leading-snug text-text-primary">
          <MathText text={q.question} />
        </p>

        {q.type === "open_ended" ? (
          <textarea
            value={openText}
            onChange={(e) => setOpenText(e.target.value)}
            disabled={showingFeedback}
            rows={4}
            placeholder={t("test.answerPlaceholder")}
            className="w-full rounded-xl border border-border bg-surface px-3.5 py-2.5 text-sm text-text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10 disabled:opacity-70"
          />
        ) : (
          <div className="space-y-2">
            {(q.options ?? []).map((opt, j) => {
              const isSelected = selected.includes(j);
              const isCorrectOpt = q.correct_indices ? q.correct_indices.includes(j) : q.correct_index === j;
              let style = "border-border bg-surface hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm";
              let badgeStyle = "border-border text-text-tertiary";
              if (showingFeedback) {
                if (isCorrectOpt) {
                  style = "border-primary bg-primary-50 text-primary-dark shadow-sm";
                  badgeStyle = "border-primary bg-primary text-white";
                } else if (isSelected) {
                  style = "border-red-200 bg-red-50 text-red-600";
                  badgeStyle = "border-red-300 bg-red-100 text-red-500";
                } else {
                  style = "border-border-light bg-surface text-text-tertiary opacity-60";
                  badgeStyle = "border-border-light text-text-tertiary";
                }
              } else if (isSelected) {
                style = "border-primary bg-primary-50 shadow-sm shadow-primary/10";
                badgeStyle = "border-primary bg-primary text-white";
              }
              return (
                <button
                  key={j}
                  onClick={() => !showingFeedback && toggleOption(j)}
                  disabled={showingFeedback}
                  className={`flex w-full items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-left text-sm font-medium transition-all ${style}`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold transition-colors ${badgeStyle}`}
                  >
                    {String.fromCharCode(65 + j)}
                  </span>
                  <span className="flex-1">
                    <MathText text={opt} />
                  </span>
                  {showingFeedback && isCorrectOpt && <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />}
                  {showingFeedback && !isCorrectOpt && isSelected && <XCircle className="h-4 w-4 shrink-0 text-red-500" />}
                </button>
              );
            })}
          </div>
        )}

        {showingFeedback && (
          <div
            className={`relative mt-4 overflow-hidden rounded-xl border p-3.5 ${
              answerForFeedback?.correct === true
                ? "border-primary/20 bg-primary-50"
                : answerForFeedback?.correct === false
                ? "border-red-200 bg-red-50"
                : "border-border-light bg-surface-muted"
            }`}
            style={{ animation: "game-round-in 0.3s ease-out" }}
          >
            {answerForFeedback?.correct === true && <Burst playKey={index} />}
            <p
              className={`mb-1 flex items-center gap-1.5 text-sm font-bold ${
                answerForFeedback?.correct === true
                  ? "text-primary-dark"
                  : answerForFeedback?.correct === false
                  ? "text-red-600"
                  : "text-text-primary"
              }`}
            >
              {answerForFeedback?.correct === true && (
                <>
                  <CheckCircle2 className="h-4 w-4" /> {t("test.correct")}
                </>
              )}
              {answerForFeedback?.correct === false && (
                <>
                  <XCircle className="h-4 w-4" /> {answerForFeedback.timedOut ? t("test.timeUp") : t("test.incorrect")}
                </>
              )}
              {answerForFeedback?.correct === null && t("test.answerRecorded")}
            </p>
            {q.type === "open_ended" && q.model_answer && (
              <p className="text-xs text-text-secondary">
                <span className="font-semibold text-text-primary">{t("test.modelAnswer")} </span>
                <MathText text={q.model_answer} />
              </p>
            )}
            {q.explanation && (
              <p className="mt-1 text-xs italic text-text-tertiary">
                <MathText text={q.explanation} />
              </p>
            )}
          </div>
        )}
      </div>

      <button
        onClick={showingFeedback ? next : submitAnswer}
        disabled={!showingFeedback && q.type !== "open_ended" && selected.length === 0}
        className="sticky bottom-4 mt-4 w-full rounded-2xl bg-primary py-3.5 text-sm font-bold text-white shadow-lg shadow-primary/30 transition hover:-translate-y-0.5 hover:bg-primary-dark disabled:translate-y-0 disabled:opacity-40 disabled:shadow-none"
      >
        {showingFeedback ? (index + 1 < total ? t("test.next") : t("test.finish")) : t("test.answerButton")}
      </button>
    </div>
  );
}
