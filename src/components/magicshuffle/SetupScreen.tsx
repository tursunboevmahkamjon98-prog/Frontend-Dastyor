"use client";

import { useState } from "react";
import { Loader2, Wand2 } from "lucide-react";
import { materialsApi } from "@/lib/api";
import { magicSfx } from "./sounds";
import { BOX_COUNT, ShuffleQuestion } from "./types";

const SUBJECTS = [
  "Математика",
  "Забони тоҷикӣ",
  "Забони англисӣ",
  "Таърих",
  "Биология",
  "География",
  "Физика",
  "Химия",
  "Информатика",
];

const GRADES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"];


const LEVELS = [
  { value: "Лёгкий", label: "Осон" },
  { value: "Средний", label: "Миёна" },
  { value: "Сложный", label: "Душвор" },
];

const ROUND_CHOICES = [5, 8, 10];


export default function SetupScreen({
  defaultSubject,
  defaultTopic,
  defaultGrade,
  onReady,
}: {
  defaultSubject?: string;
  defaultTopic?: string;
  defaultGrade?: string;
  onReady: (questions: ShuffleQuestion[]) => void;
}) {
  const [subject, setSubject] = useState(
    defaultSubject && SUBJECTS.includes(defaultSubject) ? defaultSubject : SUBJECTS[0]
  );
  const [topic, setTopic] = useState(defaultTopic ?? "");
  const [grade, setGrade] = useState(defaultGrade && GRADES.includes(defaultGrade) ? defaultGrade : "6");
  const [level, setLevel] = useState("Средний");
  const [rounds, setRounds] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    if (!topic.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await materialsApi.generateQuizSet({
        topic: topic.trim(),
        subject,
        grade,
        level,
        
        
        
        
        language: "Таджикский",
        
        
        
        count: rounds * BOX_COUNT,
      });
      const mapped: ShuffleQuestion[] = res.questions.map((q) => ({
        question: q.question,
        answers: q.options,
        correctAnswer: q.correct_index,
        explanation: q.explanation,
        subject,
      }));
      if (mapped.length === 0) {
        setError("AI ягон савол насохт. Бори дигар кӯшиш кунед.");
        return;
      }
      magicSfx.reward();
      onReady(mapped);
    } catch {
      setError("Хатогӣ рӯй дод. Бори дигар кӯшиш кунед.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full w-full flex-1 flex-col items-center overflow-y-auto px-4 py-6">
      <h1
        className="text-2xl font-black leading-tight text-white drop-shadow-[0_3px_0_rgba(0,0,0,0.35)] sm:text-4xl"
        style={{ animation: "mascot-pop 0.6s ease-out" }}
      >
        Қуттиҳои сеҳрнок
      </h1>
      <p className="mt-1.5 flex items-center gap-1.5 text-sm font-semibold text-amber-100">
        <Wand2 className="h-4 w-4" />
        AI барои шумо саволҳо месозад
      </p>

      <div className="mt-5 w-full max-w-lg space-y-3.5 rounded-3xl border border-white/20 bg-white/95 p-4 shadow-2xl sm:p-5">
        <Field label="Фан">
          <select
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full rounded-xl border-2 border-violet-200 bg-violet-50/60 px-3 py-2.5 text-sm font-semibold text-[#3b0764] outline-none focus:border-violet-500"
          >
            {SUBJECTS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Мавзӯъ">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="w-full rounded-xl border-2 border-violet-200 bg-violet-50/60 px-3 py-2.5 text-sm font-medium text-[#3b0764] outline-none focus:border-violet-500"
            placeholder="Касрҳо"
          />
        </Field>

        <Field label="Синф">
          <div className="flex flex-wrap gap-1.5">
            {GRADES.map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGrade(g)}
                className={`h-9 w-9 rounded-xl border-2 text-sm font-bold transition ${
                  grade === g
                    ? "border-violet-500 bg-violet-100 text-[#4c1d95]"
                    : "border-violet-200 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Дараҷаи душворӣ">
          <div className="grid grid-cols-3 gap-2">
            {LEVELS.map((l) => (
              <button
                key={l.value}
                type="button"
                onClick={() => setLevel(l.value)}
                className={`rounded-xl border-2 py-2 text-sm font-bold transition ${
                  level === l.value
                    ? "border-violet-500 bg-violet-100 text-[#4c1d95]"
                    : "border-violet-200 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Шумораи раундҳо">
          <div className="grid grid-cols-3 gap-2">
            {ROUND_CHOICES.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRounds(n)}
                className={`rounded-xl border-2 py-2 text-sm font-bold transition ${
                  rounds === n
                    ? "border-violet-500 bg-violet-100 text-[#4c1d95]"
                    : "border-violet-200 bg-violet-50/60 text-[#3b0764] hover:border-violet-300"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] font-medium text-violet-600">
            Барои ҳар раунд {BOX_COUNT} савол — ҳамагӣ {rounds * BOX_COUNT} савол.
          </p>
        </Field>

        {error && <p className="rounded-xl bg-red-50 px-3 py-2 text-center text-xs font-bold text-red-700">{error}</p>}
      </div>

      <button
        type="button"
        onClick={generate}
        disabled={!topic.trim() || busy}
        className="mt-4 flex w-full max-w-lg items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 py-4 text-base font-black text-white shadow-[0_6px_0_rgba(180,83,9,0.9),0_14px_28px_rgba(0,0,0,0.4)] transition hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-[0_2px_0_rgba(180,83,9,0.9)] disabled:opacity-40 disabled:shadow-none"
      >
        {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Wand2 className="h-5 w-5" />}
        {busy ? "AI саволҳо месозад..." : "Оғози бозӣ"}
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-left">
      <span className="mb-1 block text-[11px] font-black uppercase tracking-wide text-fuchsia-700">{label}</span>
      {children}
    </label>
  );
}
