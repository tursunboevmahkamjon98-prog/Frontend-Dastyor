"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { Loader2, Download, Check, Sparkles, ArrowRight, ChevronDown, Layers } from "lucide-react";
import {
  materialsApi, downloadAllZip, ApiError, type GenerateAllResult, type GenerationQuote, type MaterialType,
} from "@/lib/api";
import Mascot from "@/components/Mascot";
import CreateModeTabs from "@/components/dashboard/CreateModeTabs";
import { ErrorNote } from "@/components/ui";
import { useT } from "@/lib/i18n";
import { consumeWasBackNavigation } from "@/lib/back-navigation";
import {
  MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY, LANGUAGES, LEVELS, CLASSES, SUBJECTS,
  TEST_TYPES, TEST_TYPE_LABEL_KEYS,
} from "@/lib/material-types";

type CreatableType = Exclude<MaterialType, "igra">;
const TYPES: CreatableType[] = ["konspekt", "lektsiya", "test", "prezentatsiya", "amaliy"];
const TYPE_ART: Record<CreatableType, string> = {
  konspekt: "/soft3d/book.webp",
  lektsiya: "/soft3d/notebook.webp",
  test: "/soft3d/quiz.webp",
  prezentatsiya: "/soft3d/presentation.webp",
  amaliy: "/soft3d/notebook.webp",
};

const COUNT_PRESETS = [5, 10, 15];
const RESULT_STORAGE_KEY = "dastyor:create:result";

function loadPersistedResult(): { topic: string; selected?: CreatableType[]; result: GenerateAllResult } | null {
  if (typeof window === "undefined") return null;
  try {
    if (!consumeWasBackNavigation()) return null;
    const raw = sessionStorage.getItem(RESULT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/* The create screen, redrawn as a workspace rather than a settings form.
 *
 * The generation contract is byte-for-byte what it was: the same
 * materialsApi.generateAll call, the same required fields, the same
 * validation, the same persisted-result-on-back behaviour. Everything
 * below the state declarations is new presentation around unchanged
 * logic — a bigger, primary topic field instead of one input among six
 * equals; grade and subject as an opened panel instead of a native
 * <select> that cannot be restyled; a sticky action bar so the commit
 * point is never scrolled out of view; and a loading state built from
 * an indeterminate loading view, because generate-all emits no progress events.
 */
export default function CreatePage() {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();

  const persisted = useState(loadPersistedResult)[0];
  const [topic, setTopic] = useState(persisted?.topic ?? params.get("topic") ?? "");
  const [grade, setGrade] = useState(CLASSES[6]);
  const [subject, setSubject] = useState(SUBJECTS[0]);
  const [language, setLanguage] = useState(LANGUAGES[0]);

  const [selected, setSelected] = useState<CreatableType[]>(() => {
    if (persisted?.selected) return persisted.selected;
    const wanted = params.get("type");
    if (wanted === "all") return [...TYPES];
    if (wanted && (TYPES as string[]).includes(wanted)) return [wanted as CreatableType];
    return [];
  });
  const [slideCount, setSlideCount] = useState(10);
  const [questionCount, setQuestionCount] = useState(10);
  const [testType, setTestType] = useState("mixed");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateAllResult | null>(persisted?.result ?? null);
  const [zipping, setZipping] = useState(false);
  const [quoteState, setQuoteState] = useState<{
    key: string; version: number; quote?: GenerationQuote; error?: boolean;
  } | null>(null);
  const [quoteVersion, setQuoteVersion] = useState(0);

  const allChosen = selected.length === TYPES.length;
  const selectionKey = selected.join("|");
  const currentQuoteState = quoteState?.key === selectionKey && quoteState.version === quoteVersion
    ? quoteState : null;
  const quote = currentQuoteState?.quote;

  useEffect(() => {
    if (!selectionKey) return;
    const controller = new AbortController();
    const types = selectionKey.split("|") as CreatableType[];
    materialsApi.quote(types, controller.signal)
      .then((value) => setQuoteState({ key: selectionKey, version: quoteVersion, quote: value }))
      .catch(() => {
        if (!controller.signal.aborted) {
          setQuoteState({ key: selectionKey, version: quoteVersion, error: true });
        }
      });
    return () => controller.abort();
  }, [selectionKey, quoteVersion]);

  function toggle(type: CreatableType) {
    setSelected((prev) =>
      prev.includes(type) ? prev.filter((x) => x !== type) : [...prev, type],
    );
    setQuoteVersion((version) => version + 1);
  }

  function selectAllOrClear() {
    setSelected(allChosen ? [] : [...TYPES]);
    setQuoteVersion((version) => version + 1);
  }

  async function submit() {
    if (!topic.trim()) {
      setError(t("cur.topicRequired"));
      return;
    }
    if (selected.length === 0) {
      setError(t("create.pickAtLeastOne"));
      return;
    }
    if (!quote || !quote.affordable) return;
    setError(null);
    setSubmitting(true);
    try {
      const latestQuote = await materialsApi.quote(selected);
      if (latestQuote.required_dirams !== quote.required_dirams ||
          latestQuote.free_count !== quote.free_count ||
          latestQuote.balance_dirams !== quote.balance_dirams ||
          !latestQuote.affordable) {
        setQuoteState({ key: selectionKey, version: quoteVersion, quote: latestQuote });
        setError(t("create.quoteChanged"));
        return;
      }
      const res = await materialsApi.generateAll({
        topic, subject, language, grade,
        level: LEVELS[1],
        slide_count: slideCount,
        question_count: questionCount,
        test_type: testType,
        types: selected,
      });
      setResult(res);
      try {
        sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify({ topic, selected, result: res }));
      } catch {
        /* sessionStorage can throw in private browsing; losing the
         * restore-on-back convenience is harmless. */
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setError(t("create.quoteChanged"));
        setQuoteVersion((version) => version + 1);
      } else {
        setError(err instanceof ApiError ? err.message : t("common.error"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadZip() {
    if (!result) return;
    setError(null);
    setZipping(true);
    try {
      await downloadAllZip({
        topic, language,
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
    return <GeneratingView topic={topic} subject={subject} grade={grade} types={selected} />;
  }

  if (result) {
    const made = TYPES.filter((type) => result.content[type]);
    const failed = TYPES.filter((type) => !result.content[type] && selected.includes(type));
    return (
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-5xl flex-col justify-center px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-7 flex items-center gap-4">
          <Mascot mood={made.length === 0 ? "sad" : failed.length === 0 ? "celebrating" : "idle"} size={76} />
          <div>
            <h1 className="text-heading font-semibold text-text-primary">
              {made.length === 0 ? t("create.failedToCreate") : failed.length > 0 ? t("create.partiallyDone") : t("create.done")}
            </h1>
            <p className="text-meta text-text-secondary">«{topic}»</p>
          </div>
          {made.length > 1 && (
            <button
              onClick={downloadZip}
              disabled={zipping}
              className="ml-auto hidden shrink-0 items-center gap-2 rounded-xl border border-primary/30 bg-primary-50 px-4 py-2.5 text-meta font-semibold text-primary-accent transition-colors duration-150 hover:bg-primary/10 disabled:opacity-60 sm:flex"
            >
              {zipping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              {zipping ? t("cur.archiving") : t("cur.downloadZip")}
            </button>
          )}
        </div>

        {error && <ErrorNote>{error}</ErrorNote>}

        {made.length > 1 && (
          <button
            onClick={downloadZip}
            disabled={zipping}
            className="mb-6 flex w-full items-center justify-center gap-2 rounded-xl border border-primary/30 bg-primary-50 py-3 text-meta font-semibold text-primary-accent transition-colors duration-150 hover:bg-primary/10 disabled:opacity-60 sm:hidden"
          >
            {zipping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {zipping ? t("cur.archiving") : t("cur.downloadZip")}
          </button>
        )}

        {made.length === 1 ? (
          (() => {
            const type = made[0];
            const cfg = MATERIAL_TYPE_CONFIG[type];
            const id = result.ids?.[type];
            const Icon = cfg.icon;
            return (
              <button
                onClick={() => id && router.push(`/dashboard/materials/${type}/${id}`)}
                disabled={!id}
                className="group flex w-full flex-col items-start gap-4 overflow-hidden rounded-card border border-border-light bg-surface p-5 text-left shadow-card transition-colors duration-150 hover:border-border disabled:opacity-60 sm:flex-row sm:items-center sm:p-6"
              >
                <span className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl ${cfg.bg}`}>
                  <Icon className={`h-8 w-8 ${cfg.color}`} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-subheading font-semibold text-text-primary">{t(MATERIAL_TYPE_LABEL_KEY[type])}</span>
                  <span className="block text-meta text-text-secondary">{subject} · {grade}</span>
                </span>
                <span className="flex shrink-0 items-center gap-1.5 rounded-control bg-primary px-4 py-2.5 text-meta font-semibold text-white transition-colors duration-150 group-hover:bg-primary-dark">
                  {t("lessons.open")}
                  <ArrowRight className="h-4 w-4" />
                </span>
              </button>
            );
          })()
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {made.map((type) => {
              const cfg = MATERIAL_TYPE_CONFIG[type];
              const id = result.ids?.[type];
              const Icon = cfg.icon;
              return (
                <li key={type}>
                  <button
                    onClick={() => id && router.push(`/dashboard/materials/${type}/${id}`)}
                    disabled={!id}
                    className="group flex w-full flex-col overflow-hidden rounded-card border border-border-light bg-surface text-left transition-colors duration-150 hover:border-border disabled:opacity-60"
                  >
                    <span className={`block h-1.5 w-full ${cfg.bg}`} aria-hidden />
                    <span className="flex flex-1 items-center gap-3 p-4">
                      <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-control ${cfg.bg}`}>
                        <Icon className={`h-5 w-5 ${cfg.color}`} />
                      </span>
                      <span className="flex-1 font-semibold text-text-primary">{t(MATERIAL_TYPE_LABEL_KEY[type])}</span>
                      <ArrowRight className="h-4 w-4 shrink-0 text-text-tertiary transition-transform duration-150 group-hover:translate-x-0.5" />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {failed.length > 0 && (
          <p className="mt-4 rounded-control bg-surface-muted px-4 py-3 text-micro text-text-secondary">
            {t("create.failedPrefix")} {failed.map((type) => t(MATERIAL_TYPE_LABEL_KEY[type])).join(", ")}.
            {" "}{t("create.failedSuffix")}
          </p>
        )}

        <button
          onClick={() => {
            setResult(null);
            if (made.length > 0) setTopic("");
            setQuoteVersion((version) => version + 1);
            try {
              sessionStorage.removeItem(RESULT_STORAGE_KEY);
            } catch {
              /* see above */
            }
          }}
          className="mt-6 w-full rounded-xl border border-border bg-surface py-3 text-meta font-semibold text-text-primary transition-colors duration-150 hover:bg-surface-muted sm:w-auto sm:px-6"
        >
          {made.length === 0 ? t("create.tryAgain") : t("create.makeMore")}
        </button>
      </div>
    );
  }

  const count = selected.length;
  const summary = [topic.trim() || null, grade, subject].filter(Boolean).join(" · ");

  return (
    <div className="create-page mx-auto max-w-6xl px-4 pb-8 pt-6 sm:px-6 sm:pt-8 lg:px-8">
      <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-micro font-semibold uppercase tracking-[0.16em] text-primary-accent">{t("home.aiWorkspace")}</p>
          <h1 className="text-title font-semibold text-text-primary sm:text-display">{t("create.title")}</h1>
          <p className="mt-1 text-meta text-text-secondary sm:text-body">{t("create.prompt")}</p>
        </div>
        <div className="hidden sm:block"><Mascot mood="idle" size={72} /></div>
      </header>

      <CreateModeTabs mode="ai" />

      {error && <ErrorNote>{error}</ErrorNote>}

      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="min-w-0">

      {/* ---- The hero: the one thing only the teacher knows ---- */}
      <section className="soft-compose-panel mb-6 rounded-card border p-5 shadow-card sm:p-7">
        <p className="mb-3 text-micro font-semibold tracking-widest text-primary-accent">01 / 04</p>
        <div className="mb-3 flex items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-primary-50">
            <Sparkles className="h-4 w-4 text-primary-accent" strokeWidth={2} />
          </span>
          <label htmlFor="topic-field" className="text-subheading font-semibold text-text-primary">
            {t("create.topicTitle")}
          </label>
        </div>
        <AutoGrowField id="topic-field" value={topic} onChange={setTopic} placeholder={t("create.topicPlaceholder")} />
        <p className="mt-2 text-micro text-text-tertiary">{t("create.topicSubtitle")}</p>
      </section>

      {/* ---- Grade / subject / language, as real controls ----
       * Language gets its own row rather than a third of this one: three
       * Cyrillic language names ("Таджикский", "Английский") need more
       * room per option than a one-of-three-columns segmented control
       * can spare without truncating the very words it exists to show. */}
      <p className="mb-3 text-micro font-semibold tracking-widest text-primary-accent">02 / 04</p>
      <section className="mb-3 grid gap-3 sm:grid-cols-2">
        <FieldMenu label={t("create.gradeTitle")} value={grade} options={CLASSES} onChange={setGrade} />
        <FieldMenu label={t("create.subjectTitle")} value={subject} options={SUBJECTS} onChange={setSubject} />
      </section>
      <section className="mb-6 sm:max-w-sm">
        <LanguagePicker label={t("create.languageTitle")} value={language} options={LANGUAGES} onChange={setLanguage} />
      </section>

      {/* ---- Material types ---- */}
      <section className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="mb-1 text-micro font-semibold tracking-widest text-primary-accent">03 / 04</p>
            <h2 className="text-subheading font-semibold text-text-primary">{t("create.typesTitle")}</h2>
          </div>
          <button
            type="button"
            onClick={selectAllOrClear}
            className="text-micro font-semibold text-primary-accent transition-colors duration-150 hover:text-primary-dark"
          >
            {allChosen ? t("create.clearAll") : t("create.selectAll")}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <button
            type="button"
            onClick={selectAllOrClear}
            aria-pressed={allChosen}
            className={`group relative flex flex-col items-start gap-2.5 overflow-hidden rounded-card border p-4 text-left transition-all duration-150 ${
              allChosen
                ? "border-primary bg-primary text-white shadow-card"
                : "border-border-light bg-gradient-to-br from-primary-50 to-surface hover:border-border"
            }`}
          >
            <span
              className={`flex h-10 w-10 items-center justify-center rounded-control transition-colors duration-150 ${
                allChosen ? "bg-white/20" : "bg-primary-50"
              }`}
            >
              <Layers className={`h-5 w-5 ${allChosen ? "text-white" : "text-primary-accent"}`} strokeWidth={2} />
            </span>
            <span className={`text-meta font-semibold ${allChosen ? "text-white" : "text-text-primary"}`}>
              {t("create.allAtOnce")}
            </span>
            <span className={`text-micro leading-snug ${allChosen ? "text-white/80" : "text-text-tertiary"}`}>
              {t("create.allAtOnceDesc")}
            </span>
            {allChosen && (
              <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-white/25">
                <Check className="h-3 w-3 text-white" />
              </span>
            )}
            <Image src="/soft3d/teacher-hero.webp" alt="" aria-hidden="true" width={160} height={108} sizes="80px" className="absolute -bottom-2 -right-2 h-16 w-20 object-contain opacity-80" />
          </button>

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
                className={`group relative flex flex-col items-start gap-2.5 overflow-hidden rounded-card border p-4 text-left transition-all duration-150 ${
                  on
                    ? "shadow-card"
                    : "border-border-light bg-surface hover:-translate-y-0.5 hover:border-border hover:shadow-card"
                }`}
                style={on ? {
                  borderColor: `var(${cfg.accentVar})`,
                  backgroundColor: `color-mix(in srgb, var(${cfg.accentVar}) 12%, var(--color-surface))`,
                } : undefined}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-control transition-colors duration-150 ${on ? "text-white" : cfg.bg}`}
                  style={on ? { backgroundColor: `var(${cfg.accentVar})` } : undefined}
                >
                  <Icon className={`h-5 w-5 ${on ? "text-white" : cfg.color}`} strokeWidth={2} />
                </span>
                <span className="text-meta font-semibold text-text-primary">{t(MATERIAL_TYPE_LABEL_KEY[type])}</span>
                <Image src={TYPE_ART[type]} alt="" aria-hidden="true" width={112} height={112} sizes="56px" className="absolute -bottom-2 -right-2 h-16 w-16 object-contain drop-shadow-[0_6px_8px_rgba(64,44,43,0.12)]" />
                {on && (
                  <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full text-white" style={{ backgroundColor: `var(${cfg.accentVar})` }}>
                    <Check className="h-3 w-3" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </section>

      {(selected.includes("prezentatsiya") || selected.includes("test")) && (
        <section className="mb-6 rounded-card border border-border-light bg-surface p-5 sm:p-6">
          {selected.includes("prezentatsiya") && (
            <CountPicker label={t("create.slidesTitle")} value={slideCount} onChange={setSlideCount} />
          )}
          {selected.includes("test") && (
            <>
              <CountPicker label={t("create.questionCount")} value={questionCount} onChange={setQuestionCount} />
              <div>
                <label className="mb-2 block text-meta font-semibold text-text-primary">{t("create.questionType")}</label>
                <div className="flex flex-wrap gap-2">
                  {TEST_TYPES.map((tt) => (
                    <button
                      key={tt.value}
                      type="button"
                      onClick={() => setTestType(tt.value)}
                      className={`rounded-control border px-3.5 py-2 text-micro font-semibold transition-colors duration-150 ${
                        testType === tt.value
                          ? "border-primary bg-primary text-white"
                          : "border-border bg-surface text-text-primary hover:border-primary/40"
                      }`}
                    >
                      {t(TEST_TYPE_LABEL_KEYS[tt.value])}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </section>
      )}

        </div>

        <aside className="lg:sticky lg:top-24" aria-label={t("create.quoteTitle")}>

        <section className="rounded-card border border-border-light bg-surface p-5 shadow-card-lift sm:p-6" aria-live="polite">
          <p className="mb-1 text-micro font-semibold tracking-widest text-primary-accent">04 / 04</p>
          <h2 className="text-subheading font-semibold text-text-primary">{t("create.quoteTitle")}</h2>
          {count === 0 && <p className="mt-3 text-meta text-text-secondary">{t("create.pickAtLeastOne")}</p>}
          {count > 0 && !currentQuoteState && <p className="mt-3 text-meta text-text-secondary">{t("create.quoteLoading")}</p>}
          {currentQuoteState?.error && (
            <div className="mt-2 flex flex-wrap items-center gap-3 text-meta text-text-secondary">
              <span>{t("create.quoteError")}</span>
              <button type="button" onClick={() => setQuoteVersion((version) => version + 1)}
                className="font-semibold text-primary-accent underline">{t("create.quoteRetry")}</button>
            </div>
          )}
          {quote && (
            <>
              <div className="mt-5 rounded-control bg-surface-muted p-4">
                <p className="text-micro font-medium text-text-secondary">{t("create.quoteTotal")}</p>
                <p className="mt-1 text-heading font-semibold tabular-nums text-text-primary">{(quote.required_dirams / 100).toFixed(2)} <span className="text-meta">{t("nav.somoni")}</span></p>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-micro text-text-secondary">
                  <span>{t("create.quoteBalance")}: <strong className="tabular-nums text-text-primary">{(quote.balance_dirams / 100).toFixed(2)} {t("nav.somoni")}</strong></span>
                  <span>{t("create.quoteFree")}: <strong className="text-text-primary">{quote.free_count}</strong></span>
                  <span>{t("create.quotePaid")}: <strong className="text-text-primary">{quote.paid_count}</strong></span>
                </div>
              </div>
              <ul className="mt-4 space-y-2">
                {quote.items.map((item) => (
                  <li key={item.material_type} className="flex justify-between gap-3 text-micro text-text-secondary">
                    <span>{t(MATERIAL_TYPE_LABEL_KEY[item.material_type])}</span><span className="shrink-0 font-medium text-text-primary">{item.was_free
                      ? t("create.quoteFreeItem")
                      : `${(item.price_dirams / 100).toFixed(2)} ${t("nav.somoni")}`}</span>
                  </li>
                ))}
              </ul>
              <p className={`mt-3 text-meta font-medium ${quote.affordable ? "text-text-secondary" : "text-error"}`}>
                {quote.affordable ? t("create.quoteNotReserved") : t("create.quoteInsufficient")}
              </p>
              {!quote.affordable && <button type="button" onClick={() => router.push("/dashboard/billing")}
                className="mt-2 text-meta font-semibold text-primary-accent underline">{t("create.quoteTopUp")}</button>}
            </>
          )}
      <div className="mt-4 border-t border-border-light pt-4">
          <p className="mb-3 text-meta text-text-secondary">
            {summary || t("create.topicSubtitle")}
          </p>
          <button
            onClick={submit}
            disabled={!topic.trim() || count === 0 || !quote?.affordable || submitting}
            className="flex w-full items-center justify-center gap-2 rounded-control bg-primary px-6 py-3 text-meta font-semibold text-white transition-colors duration-150 hover:bg-primary-dark disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-text-tertiary"
          >
            <Sparkles className="h-4 w-4" />
            {count <= 1 && selected[0]
              ? `${t("create.submit")} ${t(MATERIAL_TYPE_LABEL_KEY[selected[0]]).toLowerCase()}`
              : `${t("create.submit")}${count > 1 ? ` ${count}` : ""}`}
          </button>
        </div>
        </section>
        </aside>
      </div>
    </div>
  );
}

/* A textarea that grows with its content instead of scrolling inside a
 * fixed-height box — the topic is the one field in this form that can
 * reasonably run to a full sentence ("Сложение и вычитание дробей с
 * разными знаменателями"), and a single-line input would have started
 * scrolling horizontally on exactly that case. */
function AutoGrowField({
  id, value, onChange, placeholder,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  return (
    <textarea
      id={id}
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={1}
      maxLength={200}
      autoFocus
      className="max-h-[11.25rem] min-h-[2.75rem] w-full resize-none bg-transparent text-heading font-medium leading-snug text-text-primary outline-none placeholder:text-text-tertiary"
    />
  );
}

/* A dropdown for the two fields with too many options for a segmented
 * row (11 grades, 14 subjects) — same role a native <select> played
 * before, but one that can actually carry the app's own radius, shadow
 * and type scale instead of rendering as the browser's own control.
 */
function FieldMenu({
  label, value, options, onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={boxRef} className="relative">
      <p className="mb-1.5 text-micro font-semibold uppercase tracking-wide text-text-tertiary">{label}</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 rounded-control border border-border bg-surface px-4 py-3 text-body font-medium text-text-primary transition-colors duration-150 hover:border-primary/40"
      >
        <span className="truncate">{value}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-text-tertiary transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full z-30 mt-2 max-h-64 overflow-y-auto rounded-card border border-border-light bg-surface p-1.5 shadow-float">
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => {
                onChange(opt);
                setOpen(false);
              }}
              className={`flex w-full items-center justify-between gap-2 rounded-control px-3 py-2 text-left text-meta transition-colors duration-150 ${
                opt === value ? "bg-primary-50 font-semibold text-primary-accent" : "text-text-primary hover:bg-surface-muted"
              }`}
            >
              {opt}
              {opt === value && <Check className="h-3.5 w-3.5 shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* Only three languages, so a segmented row reads faster than a menu
 * that opens and closes for a one-tap choice. */
function LanguagePicker({
  label, value, options, onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 text-micro font-semibold uppercase tracking-wide text-text-tertiary">{label}</p>
      <div className="flex gap-1.5 rounded-control border border-border bg-surface-muted p-1">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={`min-w-0 flex-1 truncate rounded-[0.4rem] px-1.5 py-2.5 text-micro font-semibold transition-colors duration-150 sm:text-meta ${
              opt === value ? "bg-surface text-primary-accent shadow-card" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {opt}
          </button>
        ))}
      </div>
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
  const custom = !COUNT_PRESETS.includes(value);
  return (
    <div className="mb-5">
      <label className="mb-2 block text-meta font-semibold text-text-primary">{label}</label>
      <div className="flex flex-wrap items-center gap-2">
        {COUNT_PRESETS.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`min-w-[3.5rem] rounded-control border px-4 py-2 text-meta font-semibold transition-colors duration-150 ${
              value === n ? "border-primary bg-primary text-white" : "border-border bg-surface text-text-primary hover:border-primary/40"
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
          placeholder="Своё"
          className={`w-24 rounded-control border px-3 py-2 text-meta outline-none transition-colors duration-150 ${
            custom ? "border-primary bg-primary-50 text-text-primary" : "border-border bg-surface"
          }`}
        />
      </div>
    </div>
  );
}


/* The line widths the central sheet "writes" — fixed, not random, so the
 * animation looks like a drawn page of text rather than static bars
 * jittering on every re-render. */
const LINE_WIDTHS = ["86%", "62%", "94%", "48%", "72%"];

/* Show the actual request and selected types while generate-all runs.
 * The API sends no progress events, so no stage is marked complete. */
function GeneratingView({
  topic, subject, grade, types,
}: {
  topic: string;
  subject: string;
  grade: string;
  types: CreatableType[];
}) {
  const t = useT();
  const chipTypes = types.slice(0, 3);

  return (
    <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-5xl flex-col justify-center px-4 py-10 sm:px-6 lg:px-8">
      <div className="grid gap-10 lg:grid-cols-[21rem_minmax(0,1fr)] lg:items-start lg:gap-12">
        {/* ---- The central visual: a page being written, not a character ---- */}
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="relative flex h-72 w-72 shrink-0 items-center justify-center sm:h-80 sm:w-80">
            <div className="create-loading-glow absolute inset-0 rounded-full bg-primary/10 blur-3xl" aria-hidden />

            <div
              className="absolute h-56 w-40 -rotate-6 rounded-card border border-border-light bg-surface shadow-card"
              aria-hidden
            />
            <div
              className="absolute h-56 w-40 rotate-6 rounded-card border border-border-light bg-surface shadow-card"
              aria-hidden
            />

            <div className="relative h-60 w-44 overflow-hidden rounded-card border border-border-light bg-surface shadow-float">
              <div className="h-2.5 w-full bg-primary" />
              <div className="space-y-3 p-4">
                {LINE_WIDTHS.map((w, i) => (
                  <div key={i} className="h-2 overflow-hidden rounded-full bg-surface-muted">
                    <div
                      className="create-line-grow h-full origin-left rounded-full bg-primary-50"
                      style={{ width: w, animationDelay: `${i * 0.28}s` }}
                    />
                  </div>
                ))}
              </div>
            </div>

            {chipTypes.map((type, i) => {
              const cfg = MATERIAL_TYPE_CONFIG[type];
              const Icon = cfg.icon;
              const positions = [
                "left-2 top-4",
                "right-2 top-1/2 -translate-y-1/2",
                "left-6 bottom-2",
              ];
              return (
                <span
                  key={type}
                  className={`create-chip-bob absolute flex h-11 w-11 items-center justify-center rounded-full border border-border-light bg-surface shadow-card ${positions[i]}`}
                  style={{ animationDelay: `${i * 0.4}s` }}
                  aria-hidden
                >
                  <Icon className={`h-5 w-5 ${cfg.color}`} strokeWidth={2} />
                </span>
              );
            })}
          </div>

          <h1 className="mt-6 text-heading font-semibold text-text-primary">{t("create.generating")}</h1>
          <p className="mt-1 text-meta text-text-secondary">{t("create.generatingHint")}</p>
        </div>

        {/* ---- Request details and selected materials ---- */}
        <div className="w-full min-w-0">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-4 rounded-card border border-border-light bg-surface p-5 sm:grid-cols-4 sm:p-6">
            <DetailField label={t("create.topicTitle")} value={topic} wide />
            <DetailField label={t("create.subjectTitle")} value={subject} />
            <DetailField label={t("create.gradeTitle")} value={grade} />
          </dl>

          <div className="mt-4">
            <div className="rounded-card border border-border-light bg-surface p-5 sm:p-6">
              <p className="mb-4 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
                {t("create.typesTitle")}
              </p>
              <ul className="space-y-2">
                {types.map((type) => {
                  const cfg = MATERIAL_TYPE_CONFIG[type];
                  const Icon = cfg.icon;
                  return (
                    <li
                      key={type}
                      className="flex items-center gap-2.5 rounded-control border border-border-light bg-surface-muted px-3 py-2.5"
                    >
                      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-control ${cfg.bg}`}>
                        <Icon className={`h-3.5 w-3.5 ${cfg.color}`} strokeWidth={2} />
                      </span>
                      <span className="min-w-0 flex-1 truncate text-meta font-medium text-text-primary">
                        {t(MATERIAL_TYPE_LABEL_KEY[type])}
                      </span>
                      <span className="create-queue-dot h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailField({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "col-span-2" : undefined}>
      <dt className="text-micro font-semibold uppercase tracking-wide text-text-tertiary">{label}</dt>
      <dd className="mt-0.5 truncate text-meta font-medium text-text-primary">{value}</dd>
    </div>
  );
}
