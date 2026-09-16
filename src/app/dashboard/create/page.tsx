"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, Download, Check, Sparkles, ArrowRight } from "lucide-react";
import {
  materialsApi, downloadAllZip, ApiError, type GenerateAllResult, type MaterialType,
} from "@/lib/api";
import { useT } from "@/lib/i18n";
import { consumeWasBackNavigation } from "@/lib/back-navigation";
import {
  MATERIAL_TYPE_CONFIG, MATERIAL_TYPE_LABEL_KEY, LANGUAGES, LEVELS, CLASSES, SUBJECTS,
  TEST_TYPES, TEST_TYPE_LABEL_KEYS,
} from "@/lib/material-types";

const FIELD =
  "w-full rounded-xl border border-border bg-surface px-4 py-3 text-sm text-text-primary outline-none focus:border-primary";
const SELECT = `${FIELD} appearance-none`;


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
    const names = selected.map((type) => t(MATERIAL_TYPE_LABEL_KEY[type])).join(", ");
    return (
      <div className="mx-auto flex max-w-lg flex-col items-center px-4 pt-24 text-center sm:px-6">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
        <p className="text-lg font-bold text-text-primary">{t("create.generating")}</p>
        <p className="mt-1 text-sm text-text-secondary">{names}</p>
        <p className="mt-3 text-xs text-text-tertiary">«{topic}»</p>
        <p className="mt-1 text-xs text-text-tertiary">{t("create.generatingHint")}</p>
      </div>
    );
  }

  if (result) {
    const made = TYPES.filter((type) => result.content[type]);
    const failed = TYPES.filter((type) => !result.content[type] && selected.includes(type));
    return (
      <div className="mx-auto max-w-lg px-4 pt-8 sm:px-6">
        <h1 className="mb-1 text-2xl font-bold text-text-primary">{t("create.done")}</h1>
        <p className="mb-4 text-sm text-text-secondary">«{topic}»</p>

        {error && (
          <div className="mb-4 rounded-xl bg-primary-50 px-4 py-3 text-sm text-primary-dark">{error}</div>
        )}

        {made.length > 1 && (
          <button
            onClick={downloadZip}
            disabled={zipping}
            className="mb-6 flex w-full items-center justify-center gap-2 rounded-xl border border-primary/30 bg-primary-50 py-2.5 text-sm font-semibold text-primary transition hover:bg-primary/10 disabled:opacity-60"
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
                className="flex w-full items-center gap-3 rounded-2xl border border-border-light bg-surface p-4 text-left transition hover:shadow-sm disabled:opacity-60"
              >
                <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${cfg.bg}`}>
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
          className="mt-6 w-full rounded-xl border border-border bg-surface py-3 text-sm font-semibold text-text-primary transition hover:bg-surface-muted"
        >
          {t("create.makeMore")}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 pb-16 pt-8 sm:px-6">
      <h1 className="mb-1 text-2xl font-bold text-text-primary">{t("create.title")}</h1>
      <p className="mb-6 text-sm text-text-secondary">{t("create.prompt")}</p>

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
        <label className="text-sm font-semibold text-text-primary">Что создать</label>
        <button
          type="button"
          onClick={() => setSelected(allChosen ? [] : [...TYPES])}
          className="text-xs font-semibold text-primary hover:text-primary-dark"
        >
          {allChosen ? "Снять всё" : "Выбрать всё"}
        </button>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-2.5 sm:grid-cols-3">
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
              className={`relative flex flex-col items-start gap-2 rounded-2xl border p-3.5 text-left transition ${
                on
                  ? "border-primary bg-primary-50 shadow-sm"
                  : "border-border-light bg-surface hover:border-border"
              }`}
            >
              <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${cfg.bg}`}>
                <Icon className={`h-5 w-5 ${cfg.color}`} />
              </span>
              <span className="text-sm font-semibold text-text-primary">
                {t(MATERIAL_TYPE_LABEL_KEY[type])}
              </span>
              {on && (
                <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white">
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
                  className={`rounded-xl border px-3.5 py-2 text-sm font-semibold transition ${
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

      <button
        onClick={submit}
        disabled={!topic.trim() || selected.length === 0}
        className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
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
            className={`min-w-[3.5rem] rounded-xl border px-4 py-2 text-sm font-semibold transition ${
              value === n
                ? "border-primary bg-primary text-white"
                : "border-border bg-surface text-text-primary hover:border-primary/40"
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
            custom ? "border-primary bg-primary-50 text-text-primary" : "border-border bg-surface"
          }`}
        />
      </div>
    </div>
  );
}
