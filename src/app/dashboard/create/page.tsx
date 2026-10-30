"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Download, Check, Sparkles, ArrowRight } from "lucide-react";
import {
  materialsApi, downloadAllZip, ApiError, type GenerateAllResult, type MaterialType,
} from "@/lib/api";
import { useT } from "@/lib/i18n";
import CreateModeTabs from "@/components/dashboard/CreateModeTabs";
import { consumeWasBackNavigation } from "@/lib/back-navigation";
import {
  MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY, LANGUAGES, LEVELS, CLASSES, SUBJECTS,
  TEST_TYPES, TEST_TYPE_LABEL_KEYS,
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

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateAllResult | null>(persisted?.result ?? null);
  const [zipping, setZipping] = useState(false);

  const allChosen = selected.length === TYPES.length;

  function toggle(type: CreatableType) {
    setSelected((prev) =>
      prev.includes(type) ? prev.filter((x) => x !== type) : [...prev, type],
    );
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
    setError(null);
    setSubmitting(true);
    try {
      const res = await materialsApi.generateAll({
        topic,
        subject,
        language,
        grade,
        
        
        
        level: LEVELS[1],
        
        
        slide_count: slideCount,
        question_count: questionCount,
        test_type: testType,
        types: selected,
      });
      setResult(res);
      try {
        sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify({ topic, result: res }));
      } catch {
        
        
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("common.error"));
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
      <div className="relative mx-auto flex min-h-[min(72vh,42rem)] max-w-3xl items-center justify-center overflow-hidden px-4 py-8 text-center sm:px-6">
        <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[28rem] w-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/[0.08] blur-3xl" aria-hidden />
        <section className="relative w-full max-w-2xl overflow-hidden rounded-[2rem] border border-border-light bg-white shadow-[0_4px_0_0_var(--color-border-light),0_28px_70px_-32px_rgba(127,29,29,0.32)]" role="status" aria-live="polite" aria-busy="true">
          <div className="h-1.5 overflow-hidden bg-primary-50">
            <div className="h-full w-1/3 rounded-full bg-gradient-to-r from-primary-light to-primary shadow-[0_0_14px_rgba(220,38,38,0.4)]" style={{ animation: "lab-sweep 1.8s ease-in-out infinite" }} />
          </div>
          <div className="px-6 py-9 sm:px-12 sm:py-12">
            <div className="relative mx-auto mb-6 grid h-20 w-20 place-items-center rounded-[1.65rem] bg-gradient-to-br from-primary-50 via-white to-primary-50 shadow-[inset_0_-3px_6px_rgba(220,38,38,0.08),0_8px_24px_-12px_rgba(220,38,38,0.3)]">
              <Sparkles className="h-9 w-9 text-primary" />
              <span className="absolute -right-1 -top-1 grid h-7 w-7 place-items-center rounded-full border-2 border-white bg-white text-primary shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-text-primary sm:text-2xl">{t("create.generating")}</h1>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-text-secondary">{t("create.generatingHint")}</p>
            <div className="mt-7 flex flex-wrap justify-center gap-2">
              {selected.map((type) => {
                const { icon: Icon, bg, color } = MATERIAL_TYPE_CONFIG[type];
                return (
                  <span key={type} className={`inline-flex items-center gap-2 rounded-full border border-border-light px-3.5 py-2 text-xs font-semibold text-text-primary ${bg}`}>
                    <Icon className={`h-4 w-4 ${color}`} />
                    {t(MATERIAL_TYPE_LABEL_KEY[type])}
                  </span>
                );
              })}
            </div>
            <div className="mx-auto mt-8 max-w-md rounded-2xl border border-border-light bg-surface-muted/70 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-tertiary">{t("create.topicTitle")}</p>
              <p className="mt-1 truncate text-sm font-semibold text-text-primary">{topic}</p>
            </div>
          </div>
        </section>
      </div>
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
                onClick={() => id && router.push(`/dashboard/materials/${type}/${id}`)}
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
      <CreateModeTabs mode="ai" />

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

      <label className="mb-1.5 block text-sm font-semibold text-text-primary">Тема урока</label>
      <input
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Например: Фотосинтез"
        className={`${FIELD} mb-5 text-base`}
        autoFocus
      />

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">Класс</label>
          <select value={grade} onChange={(e) => setGrade(e.target.value)} className={SELECT}>
            {CLASSES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">Предмет</label>
          <select value={subject} onChange={(e) => setSubject(e.target.value)} className={SELECT}>
            {SUBJECTS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-text-secondary">Язык материала</label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)} className={SELECT}>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <label className="text-sm font-semibold text-text-primary">Что создать</label>
        </div>
        <button
          type="button"
          onClick={() => setSelected(allChosen ? [] : [...TYPES])}
          className="text-xs font-semibold text-primary hover:text-primary-dark"
        >
          {allChosen ? "Снять всё" : "Выбрать всё"}
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
          label="Слайдов в презентации"
          value={slideCount}
          onChange={setSlideCount}
        />
      )}
      {selected.includes("test") && (
        <>
          <CountPicker
            label="Вопросов в тесте"
            value={questionCount}
            onChange={setQuestionCount}
          />
          <div className="mb-5">
            <label className="mb-2 block text-sm font-semibold text-text-primary">
              Тип вопросов
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

      <button
        onClick={submit}
        disabled={!topic.trim() || selected.length === 0}
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-b from-primary-light to-primary py-3.5 text-sm font-semibold text-white shadow-[0_4px_0_0_var(--color-primary-dark),0_12px_24px_-6px_rgba(220,38,38,0.4)] transition-all duration-150 hover:-translate-y-0.5 hover:shadow-[0_5px_0_0_var(--color-primary-dark),0_16px_28px_-6px_rgba(220,38,38,0.45)] active:translate-y-0.5 active:shadow-[0_1px_0_0_var(--color-primary-dark)] disabled:pointer-events-none disabled:opacity-50"
      >
        <Sparkles className="h-4 w-4" />
        {selected.length === 1
          ? `${t("create.submit")} ${t(MATERIAL_TYPE_LABEL_KEY[selected[0]]).toLowerCase()}`
          : `${t("create.submit")} ${selected.length}`}
      </button>
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
          placeholder="Своё"
          className={`w-24 rounded-xl border px-3 py-2 text-sm outline-none transition ${
            custom ? "border-primary bg-primary-50 text-text-primary" : "border-border bg-white"
          }`}
        />
      </div>
    </div>
  );
}
