"use client";

import { useState } from "react";
import { FlaskConical, Play } from "lucide-react";
import { materialsApi } from "@/lib/api";
import { labSfx } from "./sounds";
import { LabQuestion, fromQuizSet } from "./types";

const SUBJECTS = [
  "Химия",
  "Физика",
  "Биология",
  "Математика",
  "География",
  "Таърих",
  "Информатика",
  "Забони тоҷикӣ",
  "Забони англисӣ",
];

const GRADES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"];

/** `value` is the key the backend prompt expects (ai_service level_map);
 * `label` is what the player reads. */
const LEVELS = [
  { value: "Лёгкий", label: "Осон" },
  { value: "Средний", label: "Миёна" },
  { value: "Сложный", label: "Душвор" },
];

const COUNTS = [5, 10, 15];

/** Настройки + the brewing scene. The whole question set is generated HERE,
 * before the lab is ever entered, and handed to the game as a finished list —
 * nothing is generated later, so the question a player is answering can never
 * change under them. */
export default function LabSetupScreen({
  defaultSubject,
  defaultTopic,
  defaultGrade,
  onReady,
  onBrewingStart,
}: {
  defaultSubject?: string;
  defaultTopic?: string;
  defaultGrade?: string;
  onReady: (questions: LabQuestion[]) => void;
  onBrewingStart: () => void;
}) {
  const [subject, setSubject] = useState(
    defaultSubject && SUBJECTS.includes(defaultSubject) ? defaultSubject : SUBJECTS[0]
  );
  const [topic, setTopic] = useState(defaultTopic ?? "");
  const [grade, setGrade] = useState(defaultGrade && GRADES.includes(defaultGrade) ? defaultGrade : "8");
  const [level, setLevel] = useState("Средний");
  const [count, setCount] = useState(10);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function begin() {
    if (!topic.trim() || busy) return;
    setBusy(true);
    setError(null);
    onBrewingStart();
    labSfx.click();
    try {
      const res = await materialsApi.generateQuizSet({
        topic: topic.trim(),
        subject,
        grade,
        level,
        // Must be a key of the backend's LANGUAGE_NAMES map — the Tajik
        // endonym is not one, and would be rejected there.
        language: "Таджикский",
        count,
      });
      const mapped = fromQuizSet(res.questions);
      if (mapped.length === 0) {
        setError("AI ягон савол насохт. Бори дигар кӯшиш кунед.");
        setBusy(false);
        return;
      }
      onReady(mapped);
    } catch {
      setError("Хатогӣ рӯй дод. Бори дигар кӯшиш кунед.");
      setBusy(false);
    }
  }

  if (busy && !error) return <BrewingScene />;

  return (
    <div className="flex h-full w-full flex-1 flex-col items-center overflow-y-auto px-4 py-6">
      <div className="relative">
        <span className="pointer-events-none absolute -inset-6 rounded-full bg-cyan-400/25 blur-2xl" aria-hidden />
        <FlaskConical className="relative h-12 w-12 text-cyan-300" style={{ animation: "lab-bottle-idle 3s ease-in-out infinite" }} />
      </div>
      <h1
        className="mt-2 text-center text-2xl font-black leading-tight text-white drop-shadow-[0_2px_10px_rgba(56,189,248,0.5)] sm:text-4xl"
        style={{ animation: "lab-panel-in 0.6s cubic-bezier(0.22,1,0.36,1)" }}
      >
        Лабораторияи махфӣ
      </h1>
      <p className="mt-1.5 text-center text-sm font-semibold text-cyan-200/80">Танзимоти таҷриба</p>

      <div className="mt-5 w-full max-w-lg space-y-3.5 rounded-[28px] border border-white/15 bg-white/[0.07] p-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] backdrop-blur-xl sm:p-5">
        <Field label="Фан">
          <select
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2.5 text-sm font-semibold text-white outline-none backdrop-blur-sm focus:border-cyan-300"
          >
            {SUBJECTS.map((s) => (
              <option key={s} value={s} className="bg-[#0c1526] text-white">
                {s}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Мавзӯъ">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Моддаҳо"
            className="w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2.5 text-sm font-medium text-white placeholder-white/35 outline-none backdrop-blur-sm focus:border-cyan-300"
          />
        </Field>

        <Field label="Синф">
          <div className="flex flex-wrap gap-1.5">
            {GRADES.map((g) => (
              <Pill key={g} active={grade === g} onClick={() => setGrade(g)} square>
                {g}
              </Pill>
            ))}
          </div>
        </Field>

        <Field label="Дараҷаи душворӣ">
          <div className="grid grid-cols-3 gap-2">
            {LEVELS.map((l) => (
              <Pill key={l.value} active={level === l.value} onClick={() => setLevel(l.value)}>
                {l.label}
              </Pill>
            ))}
          </div>
        </Field>

        <Field label="Шумораи саволҳо">
          <div className="grid grid-cols-3 gap-2">
            {COUNTS.map((n) => (
              <Pill key={n} active={count === n} onClick={() => setCount(n)}>
                {n}
              </Pill>
            ))}
          </div>
        </Field>

        {error && (
          <p className="rounded-xl border border-rose-400/40 bg-rose-500/15 px-3 py-2 text-center text-xs font-bold text-rose-200">
            {error}
          </p>
        )}
      </div>

      <button
        type="button"
        onClick={begin}
        disabled={!topic.trim() || busy}
        className="group mt-4 flex w-full max-w-lg items-center justify-center gap-2.5 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-600 py-4 text-base font-black text-white shadow-[0_7px_0_rgba(30,64,175,0.95),0_16px_34px_rgba(8,145,178,0.45)] transition hover:-translate-y-0.5 active:translate-y-1 active:shadow-[0_2px_0_rgba(30,64,175,0.95)] disabled:opacity-40 disabled:shadow-none"
      >
        <Play className="h-5 w-5 fill-white transition-transform group-hover:scale-110" />
        Оғози таҷриба
      </button>
    </div>
  );
}

/** Shown while the AI writes the questions — a small lab animation rather
 * than a spinner and the word "Loading". */
function BrewingScene() {
  return (
    <div className="flex h-full w-full flex-1 flex-col items-center justify-center px-6">
      <div className="relative flex h-40 w-40 items-center justify-center">
        {/* orbiting molecules */}
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="absolute h-3 w-3 rounded-full"
            style={{
              background: ["#38bdf8", "#a855f7", "#34d399"][i],
              boxShadow: `0 0 14px ${["#38bdf8", "#a855f7", "#34d399"][i]}`,
              animation: `lab-orbit ${2.6 + i * 0.5}s linear infinite`,
              animationDelay: `${i * 0.4}s`,
            }}
            aria-hidden
          />
        ))}
        <span className="absolute inset-4 rounded-full bg-cyan-400/20 blur-2xl" aria-hidden />
        <FlaskConical className="relative h-16 w-16 text-cyan-200" style={{ animation: "lab-bottle-idle 2s ease-in-out infinite" }} />
        {/* rising bubbles */}
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="absolute bottom-6 h-1.5 w-1.5 rounded-full bg-cyan-200/80"
            style={{
              left: `${38 + i * 6}%`,
              ["--rise" as string]: "-70px",
              animation: `lab-bubble ${1.6 + i * 0.3}s ease-in ${i * 0.25}s infinite`,
            }}
            aria-hidden
          />
        ))}
      </div>

      <p className="mt-4 text-lg font-black text-white">Саволҳо омода мешаванд...</p>
      <p className="mt-1 text-xs font-medium text-cyan-200/70">Лаборатория тайёр карда мешавад</p>

      {/* Indeterminate sweep — honest about not knowing the duration. */}
      <div className="mt-5 h-1.5 w-56 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-cyan-300 to-violet-400"
          style={{ animation: "lab-sweep 1.4s ease-in-out infinite" }}
        />
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-left">
      <span className="mb-1.5 block text-[10px] font-black uppercase tracking-widest text-cyan-300/80">{label}</span>
      {children}
    </label>
  );
}

function Pill({
  active,
  onClick,
  children,
  square = false,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  square?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border text-sm font-bold transition active:scale-95 ${square ? "h-9 w-9" : "py-2"} ${
        active
          ? "border-cyan-300 bg-cyan-400/25 text-white shadow-[0_0_16px_rgba(56,189,248,0.45)]"
          : "border-white/20 bg-white/[0.06] text-white/70 hover:border-white/40 hover:bg-white/10"
      }`}
    >
      {children}
    </button>
  );
}
