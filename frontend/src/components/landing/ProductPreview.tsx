"use client";

import { ChevronDown, Sparkles } from "lucide-react";
import { CLASSES, LANGUAGES, SUBJECTS, LANGUAGE_LABEL_KEYS, MATERIAL_TYPE_LABEL_KEY } from "@/lib/material-types";
import { useT } from "@/lib/i18n";
import { FEATURES } from "./sections";

/* An illustration of the create screen.
 *
 * It is a drawing, not a live form — but every label, option and material
 * type in it is imported from the same constants the real screen uses, so
 * it cannot describe a product that does not exist. If a subject is
 * dropped from SUBJECTS or a type from the material list, this goes stale
 * in the same commit rather than quietly advertising it.
 *
 * Nothing here pretends to generate. The submit row is drawn in its
 * resting state and does nothing; there is no fake progress bar and no
 * invented output, because the real output is shown further down the page
 * as the actual files the product produced.
 */
export default function ProductPreview() {
  const t = useT();

  /* Picked from the real lists rather than typed in: a 7th-grade biology
   * lesson is the example, and these are the exact strings the app would
   * store for it. */
  const subject = SUBJECTS[6];
  const grade = CLASSES[6];
  const language = LANGUAGES[0];
  const ticked = new Set(["konspekt", "test", "prezentatsiya"]);

  return (
    <div
      aria-hidden
      className="overflow-hidden rounded-card border border-border bg-surface shadow-float"
    >
      {/* Window chrome, so it reads as an application screen rather than
        * as a form embedded in the marketing page itself. */}
      <div className="flex items-center gap-2 border-b border-border-light bg-surface-muted px-4 py-2.5">
        <span className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-border" />
          <span className="h-2.5 w-2.5 rounded-full bg-border" />
          <span className="h-2.5 w-2.5 rounded-full bg-border" />
        </span>
        <span className="ml-2 truncate text-micro text-text-tertiary">dastyor.tj/dashboard/create</span>
      </div>

      <div className="p-5 sm:p-7">
        <p className="text-heading font-semibold text-text-primary">{t("create.title")}</p>
        <p className="mt-0.5 text-meta text-text-secondary">{t("create.prompt")}</p>

        <label className="mt-5 block text-meta font-semibold text-text-primary">
          {t("create.topicTitle")}
        </label>
        <div className="mt-1.5 rounded-control border border-border bg-surface px-4 py-3">
          <span className="text-body text-text-primary">{t("landing.preview.topic")}</span>
          <span className="ml-0.5 inline-block h-[1.1em] w-px translate-y-[0.2em] bg-primary" />
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {[
            { label: t("create.gradeTitle"), value: grade },
            { label: t("create.subjectTitle"), value: subject },
            { label: t("create.languageTitle"), value: t(LANGUAGE_LABEL_KEYS[language]) },
          ].map((field) => (
            <div key={field.label}>
              <p className="text-micro font-medium text-text-tertiary">{field.label}</p>
              <div className="mt-1 flex items-center justify-between gap-2 rounded-control border border-border bg-surface px-3 py-2.5">
                <span className="truncate text-meta text-text-primary">{field.value}</span>
                <ChevronDown className="h-3.5 w-3.5 shrink-0 text-text-tertiary" />
              </div>
            </div>
          ))}
        </div>

        <p className="mt-5 text-meta font-semibold text-text-primary">{t("create.allAtOnce")}</p>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {FEATURES.map(({ id, icon: Icon, bg, color }) => {
            const on = ticked.has(id);
            return (
              <div
                key={id}
                className={`flex items-center gap-2.5 rounded-control border px-3 py-2.5 transition-colors ${
                  on ? "border-primary bg-primary-50" : "border-border-light bg-surface"
                }`}
              >
                <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-[0.45rem] ${bg}`}>
                  <Icon className={`h-3.5 w-3.5 ${color}`} strokeWidth={2} />
                </span>
                <span
                  className={`truncate text-meta ${
                    on ? "font-semibold text-primary-accent" : "text-text-secondary"
                  }`}
                >
                  {t(MATERIAL_TYPE_LABEL_KEY[id])}
                </span>
              </div>
            );
          })}
        </div>

        <div className="mt-5 flex items-center justify-center gap-2 rounded-control bg-primary px-5 py-3 text-body font-semibold text-white">
          <Sparkles className="h-4 w-4" strokeWidth={2.2} />
          {t("create.submit")} {ticked.size}
        </div>
      </div>
    </div>
  );
}
