"use client";

import { KONSPEKT_SECTION_KEYS, getKonspektStrings } from "@/lib/konspekt-labels";

/* The document's own table of contents — not a separate outline typed up
 * for the occasion, just KONSPEKT_SECTION_KEYS filtered down to the
 * sections this particular konspekt actually has. A lesson on a short
 * topic that skipped "Разминка" does not get a dead link to it here.
 * Labels follow the document's own content language (content.language),
 * not the viewer's interface language — a Tajik lesson gets a Tajik TOC
 * even when the teacher's own UI is set to Russian.
 */
export default function KonspektToc({ content, language }: { content: Record<string, unknown>; language?: string | null }) {
  const strings = getKonspektStrings(language);
  const present = KONSPEKT_SECTION_KEYS.filter((key) => Boolean(content[key]));
  if (present.length < 2) return null;

  return (
    <nav className="print:hidden" aria-label={strings.toc}>
      <p className="mb-2.5 px-1 text-micro font-semibold uppercase tracking-wide text-text-tertiary">
        {strings.toc}
      </p>
      <ul className="space-y-0.5 border-l border-border-light">
        {present.map((key) => (
          <li key={key}>
            <a
              href={`#${key}`}
              className="block truncate border-l-2 border-transparent py-1.5 pl-3 text-meta text-text-secondary transition-colors duration-150 hover:border-primary hover:text-text-primary"
            >
              {strings.sections[key]}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
