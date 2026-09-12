"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { LegalDoc, legalDoc } from "@/lib/legal";
import { useLocale } from "@/lib/i18n";

/** Renders one legal document (terms or privacy).
 *
 * Both pages are the same shape — a heading, a date and numbered
 * sections — so they share this component rather than duplicating the
 * markup twice. The language follows the interface language the teacher
 * already chose. */
export default function LegalPage({ docs }: { docs: Record<string, LegalDoc> }) {
  const { locale } = useLocale();
  const doc = legalDoc(docs, locale);

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-2 text-sm text-text-secondary hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Dastyor
      </Link>

      <h1 className="text-2xl font-bold text-text-primary">{doc.title}</h1>
      <p className="mt-1 text-xs text-text-tertiary">{doc.updated}</p>

      <div className="mt-7 space-y-7">
        {doc.sections.map((section) => (
          <section key={section.h}>
            <h2 className="mb-2 text-base font-semibold text-text-primary">{section.h}</h2>
            <div className="space-y-2">
              {section.p.map((line, i) => (
                <p key={i} className="text-sm leading-relaxed text-text-secondary">
                  {line}
                </p>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
