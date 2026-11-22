"use client";

import { ChevronDown, Clock3, Layers3, Users } from "lucide-react";
import {
  LESSON_FRAMEWORKS,
  lessonFrameworkFor,
  lessonLanguageKey,
  type LessonFrameworkId,
} from "@/lib/lesson-frameworks";

export interface LessonDesignContext {
  frameworkId: LessonFrameworkId;
  duration: string;
  classSize: string;
  deliveryMode: string;
  learnerProfile: string;
  existingObjectives: string;
  previouslyCovered: string;
  comingNext: string;
  priorKnowledge: string;
  assessmentContext: string;
  aiPolicy: string;
}

interface LessonDesignPanelProps {
  language: string;
  value: LessonDesignContext;
  onChange: <K extends keyof LessonDesignContext>(key: K, value: LessonDesignContext[K]) => void;
}

const FIELD =
  "w-full rounded-xl border border-border bg-white px-3.5 py-2.5 text-sm text-text-primary outline-none transition focus:border-primary focus:ring-4 focus:ring-primary/10";

const COPY = {
  ru: {
    title: "Настроить урок подробнее",
    hint: "Эти параметры помогут AI спланировать время, активности и этапы урока.",
    framework: "Педагогическая структура",
    frameworkHint: "Выберите модель — она будет использована внутри этапов конспекта.",
    duration: "Продолжительность",
    classSize: "Количество учеников",
    classSizePlaceholder: "Например: 25",
    delivery: "Формат проведения",
    learner: "Профиль учеников",
    learnerPlaceholder: "Например: начинают с нуля, уровень разный",
    objectives: "Готовые цели урока (необязательно)",
    objectivesPlaceholder: "По одной цели на строку",
    sequence: "Контекст учебной последовательности",
    previous: "Что уже изучили",
    next: "Что изучат дальше",
    prior: "Какие знания предполагаются",
    assessment: "Для какой проверки готовим",
    aiPolicy: "Правила использования AI",
    face: "Очно",
    online: "Онлайн",
    hybrid: "Смешанный формат",
    self: "Самостоятельно",
    permitted: "Можно с указанием AI",
    required: "AI нужно использовать",
    notPermitted: "AI не используется",
  },
  tg: {
    title: "Дарсро муфассал танзим кунед",
    hint: "Ин маълумот ба AI барои дуруст тақсим кардани вақт ва марҳилаҳои дарс кӯмак мекунад.",
    framework: "Сохтори педагогӣ",
    frameworkHint: "Моделро интихоб кунед — он дар марҳилаҳои консpekt истифода мешавад.",
    duration: "Давомнокӣ",
    classSize: "Шумораи хонандагон",
    classSizePlaceholder: "Масалан: 25",
    delivery: "Тарзи гузаронидан",
    learner: "Профили хонандагон",
    learnerPlaceholder: "Масалан: аз ибтидо меомӯзанд, сатҳҳо гуногунанд",
    objectives: "Мақсадҳои тайёри дарс (ихтиёрӣ)",
    objectivesPlaceholder: "Ҳар мақсад дар сатри алоҳида",
    sequence: "Контексти пайдарпайии таълим",
    previous: "Чӣ омӯхта шуд",
    next: "Баъд чӣ омӯхта мешавад",
    prior: "Дониши пешакӣ",
    assessment: "Барои кадом санҷиш омода мекунем",
    aiPolicy: "Қоидаҳои истифодаи AI",
    face: "Ҳузурӣ",
    online: "Онлайн",
    hybrid: "Омехта",
    self: "Мустақилона",
    permitted: "Бо зикри истифодаи AI иҷозат аст",
    required: "Истифодаи AI лозим аст",
    notPermitted: "AI истифода намешавад",
  },
  en: {
    title: "Fine-tune the lesson",
    hint: "These settings help AI plan realistic timing, activities and lesson stages.",
    framework: "Instructional framework",
    frameworkHint: "Choose a model — it will shape the lesson stages inside Dastyor's konspekt.",
    duration: "Duration",
    classSize: "Class size",
    classSizePlaceholder: "e.g. 25",
    delivery: "Delivery mode",
    learner: "Learner profile",
    learnerPlaceholder: "e.g. beginners, mixed ability",
    objectives: "Existing objectives (optional)",
    objectivesPlaceholder: "One objective per line",
    sequence: "Sequence context",
    previous: "Previously covered",
    next: "Coming next",
    prior: "Assumed prior knowledge",
    assessment: "Assessment this supports",
    aiPolicy: "GenAI policy",
    face: "Face-to-face",
    online: "Online synchronous",
    hybrid: "Hybrid",
    self: "Self-paced",
    permitted: "Permitted with acknowledgement",
    required: "Actively required",
    notPermitted: "Not permitted",
  },
} as const;

export default function LessonDesignPanel({ language, value, onChange }: LessonDesignPanelProps) {
  const key = lessonLanguageKey(language);
  const copy = COPY[key];
  const selected = lessonFrameworkFor(value.frameworkId);

  return (
    <details className="mb-6 rounded-2xl border border-border-light bg-white shadow-[0_2px_0_0_var(--color-border-light)]">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3.5 text-sm font-semibold text-text-primary [&::-webkit-details-marker]:hidden">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-50 text-primary">
          <Layers3 className="h-4 w-4" />
        </span>
        <span className="flex-1">
          <span className="block">{copy.title}</span>
          <span className="mt-0.5 block text-xs font-normal text-text-tertiary">{copy.hint}</span>
        </span>
        <ChevronDown className="h-4 w-4 text-text-tertiary transition-transform [[open]_&]:rotate-180" />
      </summary>

      <div className="border-t border-border-light px-4 pb-5 pt-4 sm:px-5">
        <div className="mb-5">
          <div className="mb-1.5 text-sm font-semibold text-text-primary">{copy.framework}</div>
          <p className="mb-3 text-xs text-text-tertiary">{copy.frameworkHint}</p>
          <div className="grid gap-2">
            {LESSON_FRAMEWORKS.map((framework) => {
              const active = framework.id === value.frameworkId;
              return (
                <button
                  key={framework.id}
                  type="button"
                  onClick={() => onChange("frameworkId", framework.id)}
                  className={`rounded-xl border px-3.5 py-3 text-left transition ${
                    active
                      ? "border-primary bg-primary-50 shadow-[0_2px_0_0_var(--color-primary-50)]"
                      : "border-border bg-white hover:border-primary/40 hover:bg-primary-50/40"
                  }`}
                >
                  <span className="flex items-center gap-2 text-sm font-semibold text-text-primary">
                    <span className={`h-2.5 w-2.5 rounded-full ${active ? "bg-primary" : "border border-border"}`} />
                    {framework.names[key]}
                  </span>
                  <span className="mt-1 block pl-[18px] text-xs leading-5 text-text-secondary">
                    {framework.descriptions[key]}
                  </span>
                  <span className="mt-1.5 block pl-[18px] text-[11px] leading-4 text-text-tertiary">
                    {framework.stages.join(" → ")}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 rounded-lg bg-surface-muted px-3 py-2 text-xs leading-5 text-text-secondary">
            {selected.guidance}
          </p>
        </div>

        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <label className="block text-xs font-semibold text-text-secondary">
            <span className="mb-1.5 flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" />{copy.duration}</span>
            <select className={FIELD} value={value.duration} onChange={(event) => onChange("duration", event.target.value)}>
              {["30", "45", "50", "60", "90"].map((minutes) => <option key={minutes} value={`${minutes} minutes`}>{minutes} {key === "tg" ? "дақиқа" : key === "ru" ? "минут" : "minutes"}</option>)}
            </select>
          </label>
          <label className="block text-xs font-semibold text-text-secondary">
            <span className="mb-1.5 flex items-center gap-1.5"><Users className="h-3.5 w-3.5" />{copy.classSize}</span>
            <input className={FIELD} value={value.classSize} placeholder={copy.classSizePlaceholder} onChange={(event) => onChange("classSize", event.target.value)} />
          </label>
          <label className="block text-xs font-semibold text-text-secondary">
            <span className="mb-1.5 block">{copy.delivery}</span>
            <select className={FIELD} value={value.deliveryMode} onChange={(event) => onChange("deliveryMode", event.target.value)}>
              <option value="Face-to-face">{copy.face}</option>
              <option value="Online synchronous">{copy.online}</option>
              <option value="Hybrid">{copy.hybrid}</option>
              <option value="Self-paced">{copy.self}</option>
            </select>
          </label>
        </div>

        <div className="grid gap-4">
          <label className="block text-xs font-semibold text-text-secondary">
            <span className="mb-1.5 block">{copy.learner}</span>
            <textarea className={FIELD} rows={2} value={value.learnerProfile} placeholder={copy.learnerPlaceholder} onChange={(event) => onChange("learnerProfile", event.target.value)} />
          </label>
          <label className="block text-xs font-semibold text-text-secondary">
            <span className="mb-1.5 block">{copy.objectives}</span>
            <textarea className={FIELD} rows={2} value={value.existingObjectives} placeholder={copy.objectivesPlaceholder} onChange={(event) => onChange("existingObjectives", event.target.value)} />
          </label>
        </div>

        <details className="mt-4 rounded-xl border border-border-light bg-surface-muted/30 px-3.5 py-3">
          <summary className="cursor-pointer text-xs font-semibold text-text-secondary">{copy.sequence}</summary>
          <div className="mt-3 grid gap-3">
            <label className="block text-xs font-semibold text-text-secondary"><span className="mb-1 block">{copy.previous}</span><textarea className={FIELD} rows={2} value={value.previouslyCovered} onChange={(event) => onChange("previouslyCovered", event.target.value)} /></label>
            <label className="block text-xs font-semibold text-text-secondary"><span className="mb-1 block">{copy.next}</span><textarea className={FIELD} rows={2} value={value.comingNext} onChange={(event) => onChange("comingNext", event.target.value)} /></label>
            <label className="block text-xs font-semibold text-text-secondary"><span className="mb-1 block">{copy.prior}</span><textarea className={FIELD} rows={2} value={value.priorKnowledge} onChange={(event) => onChange("priorKnowledge", event.target.value)} /></label>
            <label className="block text-xs font-semibold text-text-secondary"><span className="mb-1 block">{copy.assessment}</span><textarea className={FIELD} rows={2} value={value.assessmentContext} onChange={(event) => onChange("assessmentContext", event.target.value)} /></label>
          </div>
        </details>

        <label className="mt-4 block text-xs font-semibold text-text-secondary">
          <span className="mb-1.5 block">{copy.aiPolicy}</span>
          <select className={FIELD} value={value.aiPolicy} onChange={(event) => onChange("aiPolicy", event.target.value)}>
            <option value="Permitted with acknowledgement">{copy.permitted}</option>
            <option value="Actively required">{copy.required}</option>
            <option value="Not permitted">{copy.notPermitted}</option>
          </select>
        </label>
      </div>
    </details>
  );
}

