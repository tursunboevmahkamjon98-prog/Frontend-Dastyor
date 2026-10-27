"use client";

import { RotateCw } from "lucide-react";
import { getViewerStrings } from "@/lib/content-lang";

interface Question {
  question: string;
  type?: string;
  options?: string[];
  correct_index?: number;
  correct_indices?: number[];
  model_answer?: string;
  explanation?: string;
}

/* Moved out of the material viewer's own file and redrawn: each question
 * used to be the same bordered card every other material type uses too
 * (slide, task, section — all one box with a heading and a paragraph).
 * A test reads better as a numbered sequence — the number carries the
 * position, so the card around it is no longer needed to tell questions
 * apart, only a hairline rule between them.
 */
export default function TestViewer({
  content,
  language,
  onRegenerateQuestion,
  regeneratingQuestion,
}: {
  content: Record<string, unknown>;
  language?: string | null;
  onRegenerateQuestion?: (index: number) => void;
  regeneratingQuestion?: number | null;
}) {
  const strings = getViewerStrings(language);
  const description = content.description as string | undefined;
  const questions = (content.questions as Question[] | undefined) ?? [];

  return (
    <div>
      {description && <p className="mb-6 text-meta italic text-text-secondary">{description}</p>}
      <ol className="divide-y divide-border-light">
        {questions.map((q, i) => (
          <li key={i} className="py-5 first:pt-0">
            <div className="mb-3 flex items-start gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-50 text-meta font-semibold text-primary-accent">
                {i + 1}
              </span>
              <p className="min-w-0 flex-1 pt-0.5 text-body font-medium leading-snug text-text-primary">{q.question}</p>
              {onRegenerateQuestion && (
                <button
                  onClick={() => onRegenerateQuestion(i)}
                  disabled={regeneratingQuestion === i}
                  title={strings.regenerateQuestion}
                  className="shrink-0 rounded-control p-1.5 text-text-tertiary transition-colors duration-150 hover:bg-surface-muted hover:text-primary-accent disabled:opacity-50"
                >
                  <RotateCw className={`h-3.5 w-3.5 ${regeneratingQuestion === i ? "animate-spin" : ""}`} />
                </button>
              )}
            </div>

            {q.type === "open_ended" ? (
              q.model_answer && (
                <p className="ml-10 rounded-control bg-surface-muted px-3.5 py-2.5 text-meta text-text-secondary">
                  <span className="font-semibold text-primary-accent">{strings.answerLabel} </span>
                  {q.model_answer}
                </p>
              )
            ) : (
              <ul className="ml-10 space-y-1.5">
                {(q.options ?? []).map((opt, j) => {
                  const isCorrect = q.correct_indices ? q.correct_indices.includes(j) : q.correct_index === j;
                  return (
                    <li
                      key={j}
                      className={`flex items-baseline gap-2 rounded-control px-3 py-1.5 text-meta ${
                        isCorrect ? "bg-primary-50 font-medium text-primary-accent" : "text-text-secondary"
                      }`}
                    >
                      <span className="shrink-0 font-semibold">{String.fromCharCode(65 + j)}</span>
                      <span className="min-w-0">{opt}</span>
                    </li>
                  );
                })}
              </ul>
            )}
            {q.explanation && <p className="ml-10 mt-2 text-micro italic text-text-tertiary">{q.explanation}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
