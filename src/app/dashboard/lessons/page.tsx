"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

import { Check, Loader2, Plus } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { LESSON_TYPES, lessonsApi, type LessonDetail, type LessonSummary, type LessonType } from "@/lib/lessons-api";
import { LANGUAGES, LEVELS, MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { LANGUAGE_LABEL_KEYS, LEVEL_LABEL_KEYS } from "@/lib/material-types";
import { useLocale, useT } from "@/lib/i18n";

/* A lesson is a (subject, grade, topic) triple, not a stored row, so the
 * backend groups materials into lessons in SQL and this page reads that
 * grouping. The list call returns only a count per lesson - which of the five
 * types exist needs a second call per lesson, so each card fetches its own
 * detail the first time it scrolls into view.
 *
 * That is lazy *data*, not lazy content: the card, its topic and its counts
 * render immediately and are in the DOM for anything that does not scroll.
 * Only the per-type chips resolve from placeholder to real state. */

const SELECT =
  "rounded-control border border-border bg-surface px-3 py-2 text-meta text-text-primary outline-none transition-colors duration-150 focus:border-primary";

function LessonCard({
  lesson,
  language,
  level,
}: {
  lesson: LessonSummary;
  language: string;
  level: string;
}) {
  const t = useT();
  const { locale } = useLocale();
  const ref = useRef<HTMLLIElement>(null);
  const [detail, setDetail] = useState<LessonDetail | null>(null);
  const [busy, setBusy] = useState<LessonType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    lessonsApi
      .detail(lesson.subject, lesson.grade, lesson.topic)
      .then(setDetail)
      .catch(() => {});
  }, [lesson.subject, lesson.grade, lesson.topic]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        io.disconnect();
        load();
      }
    });
    io.observe(el);
    return () => io.disconnect();
  }, [load]);

  async function generate(type: LessonType) {
    setBusy(type);
    setError(null);
    try {
      await lessonsApi.generate({
        material_type: type,
        topic: lesson.topic,
        subject: lesson.subject,
        grade: lesson.grade,
        language,
        level,
      });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("lessons.generateFailed"));
    } finally {
      setBusy(null);
    }
  }

  const present = detail ? LESSON_TYPES.filter((type) => detail.materials[type]).length : null;
  const complete = present === LESSON_TYPES.length;

  return (
    <li
      ref={ref}
      className="rounded-card border border-border-light bg-surface p-4 transition-colors duration-150 hover:border-border sm:p-5"
    >
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="truncate text-subheading font-semibold text-text-primary">{lesson.topic}</h2>
          <p className="mt-0.5 text-meta text-text-tertiary">
            {lesson.subject} · {lesson.grade} ·{" "}
            {new Date(lesson.last_touched).toLocaleDateString(locale)}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-micro font-semibold ${
            complete ? "bg-primary-50 text-primary-accent" : "bg-surface-muted text-text-tertiary"
          }`}
        >
          {present ?? "–"}/{LESSON_TYPES.length} {t("lessons.ready")}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {LESSON_TYPES.map((type) => {
          const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
          const label = t(MATERIAL_TYPE_LABEL_KEY[type]);
          const ref_ = detail?.materials[type];

          if (!detail) {
            return (
              <span
                key={type}
                className="flex items-center gap-2 rounded-control border border-border-light px-3 py-2 text-meta text-text-tertiary"
              >
                <span className={`flex h-6 w-6 items-center justify-center rounded ${bg}`}>
                  <Icon className={`h-3.5 w-3.5 ${color}`} strokeWidth={1.9} />
                </span>
                {label}
              </span>
            );
          }

          if (ref_) {
            return (
              <Link
                key={type}
                href={`/dashboard/materials/${type}/${ref_.id}`}
                className="flex items-center gap-2 rounded-control border border-border-light bg-surface px-3 py-2 text-meta font-medium text-text-primary transition-colors duration-150 hover:bg-surface-muted"
              >
                <span className={`flex h-6 w-6 items-center justify-center rounded ${bg}`}>
                  <Icon className={`h-3.5 w-3.5 ${color}`} strokeWidth={1.9} />
                </span>
                {label}
                <Check className="h-3.5 w-3.5 text-success" strokeWidth={2.5} />
              </Link>
            );
          }

          return (
            <button
              key={type}
              type="button"
              onClick={() => generate(type)}
              disabled={busy !== null}
              className="flex items-center gap-2 rounded-control border border-dashed border-border px-3 py-2 text-meta font-medium text-text-secondary transition-colors duration-150 hover:border-primary hover:text-text-primary disabled:pointer-events-none disabled:opacity-50"
            >
              {busy === type ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary-accent" />
              ) : (
                <Plus className="h-4 w-4 text-text-tertiary" strokeWidth={2.2} />
              )}
              {busy === type ? t("lessons.generating") : label}
            </button>
          );
        })}
      </div>

      {error && <p className="mt-3 text-meta text-error">{error}</p>}
    </li>
  );
}

export default function LessonsPage() {
  const t = useT();
  const { user } = useAuth();
  const [lessons, setLessons] = useState<LessonSummary[] | null>(null);
  const [language, setLanguage] = useState(
    LANGUAGES.includes(user?.language ?? "") ? (user!.language as string) : LANGUAGES[0],
  );
  const [level, setLevel] = useState(LEVELS[1]);

  useEffect(() => {
    lessonsApi
      .list()
      .then(setLessons)
      .catch(() => setLessons([]));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 pt-8 sm:px-6 lg:max-w-4xl lg:px-10 lg:pt-12">
      <header className="mb-6">
        <h1 className="text-title font-semibold text-text-primary">{t("lessons.title")}</h1>
        <p className="mt-1 text-body text-text-secondary">{t("lessons.subtitle")}</p>
      </header>

      {/* One setting pair for the whole page: everything generated from here
        * belongs to a lesson that already exists, so the only choices left
        * are how it should read. */}
      <div className="mb-6 flex flex-wrap gap-3">
        <label className="flex items-center gap-2 text-meta text-text-secondary">
          {t("lessons.language")}
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className={SELECT}>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {t(LANGUAGE_LABEL_KEYS[l])}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-meta text-text-secondary">
          {t("lessons.level")}
          <select value={level} onChange={(e) => setLevel(e.target.value)} className={SELECT}>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {t(LEVEL_LABEL_KEYS[l])}
              </option>
            ))}
          </select>
        </label>
      </div>

      {lessons === null && <p className="text-body text-text-tertiary">{t("common.loading")}</p>}

      {lessons?.length === 0 && (
        <div className="flex flex-col items-center rounded-card border border-border-light bg-surface p-8 text-center">
          <p className="mb-4 mt-3 text-body text-text-secondary">{t("lessons.empty")}</p>
          <Link
            href="/dashboard/create"
            className="inline-flex rounded-control bg-primary px-5 py-2.5 text-body font-semibold text-white transition-colors duration-150 hover:bg-primary-dark"
          >
            {t("lessons.emptyCta")}
          </Link>
        </div>
      )}

      {lessons && lessons.length > 0 && (
        <ul className="space-y-3">
          {lessons.map((lesson) => (
            <LessonCard
              key={`${lesson.subject}|${lesson.grade}|${lesson.topic}`}
              lesson={lesson}
              language={language}
              level={level}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
