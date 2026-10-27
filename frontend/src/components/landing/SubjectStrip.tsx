"use client";

import { SUBJECTS } from "@/lib/material-types";
import { useT } from "@/lib/i18n";

/* The subject list — every subject, not a scroller.
 *
 * This is the old SubjectsCarousel, which had already stopped being a
 * carousel (the arrows hid most of the list behind a click, which is a bad
 * way to answer the one question the section exists for: "is my subject in
 * there?"). What changed here is where it lives: it was a full section
 * with its own eyebrow and heading taking ~400px of the page, and it is
 * now the base of the features band, which is where the question comes up
 * anyway. The list itself is unchanged and still complete.
 *
 * `inverse` styles it for the dark band; the default styling is kept for
 * any light surface that wants it later.
 */
export default function SubjectStrip({ inverse = false }: { inverse?: boolean }) {
  const t = useT();

  return (
    <div>
      <p
        className={`mb-3.5 text-meta font-semibold ${
          inverse ? "text-text-on-inverse" : "text-text-primary"
        }`}
      >
        {SUBJECTS.length} {t("landing.subjects.count")}{" "}
        <span className={inverse ? "text-primary-light" : "text-primary-accent"}>
          {t("landing.subjects.any")}
        </span>
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {SUBJECTS.map((subject) => (
          <li
            key={subject}
            className={`rounded-control border px-3 py-1.5 text-meta ${
              inverse
                ? "border-border-inverse bg-white/[0.04] text-text-on-inverse-muted"
                : "border-border-light bg-surface text-text-secondary"
            }`}
          >
            {subject}
          </li>
        ))}
      </ul>
    </div>
  );
}
